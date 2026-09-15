"""Real satellite change detection via Sentinel Hub's Statistical API.

Compares mean NDVI (vegetation index) over a baseline window and a current
window for a small AOI around the requested point. A significant drop in
NDVI is used as the change signal (vegetation loss / exposed soil /
excavation-scale disturbance) - this is a standard, well-established remote
sensing technique and a reasonable first real detector; it does not require
any labeled training data or a hosted ML model. `estimated_area_hectares` is
approximated from the Statistical API's histogram output (the increase in
the fraction of low-NDVI pixels between the two windows), not from
per-pixel classification.

Time windows and thresholds are fixed constants rather than configuration:
they were chosen to balance finding enough cloud-free Sentinel-2 data over
Ghana against being responsive to genuinely recent change, and are meant to
be tuned once real results are visible in production - see the constants
below.
"""

import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import get_settings
from app.services.satellite.provider import (
    ChangeDetectionOutcome,
    ObservationResult,
    SatelliteProvider,
    SatelliteProviderError,
)

AOI_HALF_SIZE_DEG = 0.005  # ~1.1km square AOI around the requested point
AOI_PIXELS_PER_SIDE = 100  # ~11m/pixel over the AOI - close to native Sentinel-2 10m resolution.
# Specified as explicit pixel width/height rather than resx/resy in metres:
# resx/resy is ambiguous (metres vs. CRS units) when bounds are given in
# EPSG:4326 lat/lon, and produced a single-pixel AOI (sampleCount=1) when
# first tried against the real API - width/height sidesteps that entirely.
BASELINE_DAYS_AGO = (240, 120)  # (from, to) days before now
CURRENT_DAYS_AGO = (120, 0)
# Wide windows (~4 months each) are needed for tropical West Africa: Sentinel-2
# revisits every ~5 days, but during the rainy season a single ~45-day window
# can have zero cloud-free passes over a small AOI even with leastCC
# mosaicking (verified empirically against real data before choosing these).

NDVI_CHANGE_THRESHOLD = 0.08  # minimum |delta mean NDVI| to call it a change
BARE_NDVI_THRESHOLD = 0.3  # pixels below this are treated as bare/disturbed
MIN_VALID_SAMPLE_FRACTION = 0.15  # below this, treat the window as too cloudy to trust

_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    // SCL (scene classification) only supports DN units, unlike the optical
    // bands - request everything as DN and convert B04/B08 to reflectance
    // ourselves (Sentinel-2 L2A scale factor is 10000) rather than mixing units.
    input: [{ bands: ["B04", "B08", "SCL"] }],
    output: [
      { id: "ndvi", bands: 1, sampleType: "FLOAT32" },
      { id: "dataMask", bands: 1 }
    ]
  };
}
function evaluatePixel(sample) {
  let red = sample.B04 / 10000;
  let nir = sample.B08 / 10000;
  let ndvi = (nir - red) / (nir + red + 0.0001);
  let cloud = (sample.SCL == 3 || sample.SCL == 8 || sample.SCL == 9 || sample.SCL == 10);
  return { ndvi: [ndvi], dataMask: [cloud ? 0 : 1] };
}
"""


def _aoi_area_hectares(lat: float, half_size_deg: float) -> float:
    lat_span_m = 2 * half_size_deg * 111_320
    lon_span_m = 2 * half_size_deg * 111_320 * math.cos(math.radians(lat))
    return round((lat_span_m * lon_span_m) / 10_000, 2)


class SentinelHubProvider(SatelliteProvider):
    name = "sentinelhub-sentinel2-l2a-ndvi"
    is_simulated = False

    def __init__(self) -> None:
        settings = get_settings()
        self._client_id = settings.sentinelhub_client_id
        self._client_secret = settings.sentinelhub_client_secret
        self._token_url = settings.sentinelhub_token_url
        self._statistics_url = settings.sentinelhub_statistics_url
        self._token: str | None = None
        self._token_expiry: float = 0.0

    def _get_token(self) -> str:
        now = time.monotonic()
        if self._token and now < self._token_expiry - 30:
            return self._token

        resp = httpx.post(
            self._token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            timeout=15.0,
        )
        if resp.status_code != 200:
            raise SatelliteProviderError(
                f"Sentinel Hub authentication failed ({resp.status_code}): {resp.text[:300]}"
            )
        data = resp.json()
        self._token = data["access_token"]
        self._token_expiry = now + float(data.get("expires_in", 3600))
        return self._token

    def _query_window(self, lat: float, lon: float, date_from: datetime, date_to: datetime) -> dict:
        token = self._get_token()
        d = AOI_HALF_SIZE_DEG
        ring = [
            [lon - d, lat - d], [lon + d, lat - d], [lon + d, lat + d], [lon - d, lat + d], [lon - d, lat - d],
        ]
        window_days = max((date_to - date_from).days, 1)

        body = {
            "input": {
                "bounds": {
                    "geometry": {"type": "Polygon", "coordinates": [ring]},
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
                },
                "data": [{"type": "sentinel-2-l2a", "dataFilter": {"mosaickingOrder": "leastCC"}}],
            },
            "aggregation": {
                "timeRange": {
                    "from": date_from.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "to": date_to.strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
                "aggregationInterval": {"of": f"P{window_days}D"},
                "evalscript": _EVALSCRIPT,
                "width": AOI_PIXELS_PER_SIDE,
                "height": AOI_PIXELS_PER_SIDE,
            },
            "calculations": {
                "default": {"histograms": {"default": {"nBins": 20, "lowEdge": -1.0, "highEdge": 1.0}}}
            },
        }

        resp = httpx.post(
            self._statistics_url, json=body, headers={"Authorization": f"Bearer {token}"}, timeout=45.0
        )
        if resp.status_code != 200:
            raise SatelliteProviderError(
                f"Sentinel Hub statistics request failed ({resp.status_code}): {resp.text[:400]}"
            )
        return resp.json()

    @staticmethod
    def _extract_band_stats(response_json: dict) -> dict | None:
        buckets = response_json.get("data") or []
        if not buckets:
            return None
        outputs = buckets[0].get("outputs", {})
        ndvi_output = outputs.get("ndvi", {})
        bands = ndvi_output.get("bands", {})
        band = bands.get("B0")
        if not band:
            return None
        raw_stats = band.get("stats")
        if not raw_stats:
            return None

        # The Statistical API returns numeric fields as strings for some
        # collections/versions - normalize everything to real numbers so
        # arithmetic downstream is safe regardless.
        try:
            stats = {
                "mean": float(raw_stats["mean"]),
                "min": float(raw_stats.get("min", 0)),
                "max": float(raw_stats.get("max", 0)),
                "stDev": float(raw_stats.get("stDev", 0)),
                "sampleCount": int(float(raw_stats.get("sampleCount", 0))),
                "noDataCount": int(float(raw_stats.get("noDataCount", 0))),
            }
        except (KeyError, TypeError, ValueError):
            return None

        if stats["sampleCount"] == 0 or math.isnan(stats["mean"]):
            return None

        # sampleCount is the TOTAL pixel count for the AOI grid (confirmed
        # empirically against the real API - it stays constant regardless of
        # cloud cover), and noDataCount is how many of those were masked out
        # (cloud/shadow/cirrus per the evalscript's dataMask). Valid pixels
        # are therefore the difference, not the sum.
        valid_count = max(stats["sampleCount"] - stats["noDataCount"], 0)
        valid_fraction = valid_count / max(stats["sampleCount"], 1)
        if valid_fraction < MIN_VALID_SAMPLE_FRACTION:
            return None

        stats["_valid_fraction"] = valid_fraction
        stats["_histogram"] = band.get("histogram", {}).get("bins", [])
        return stats

    @staticmethod
    def _bare_fraction(stats: dict) -> float:
        bins = stats.get("_histogram") or []
        try:
            counts = [(float(b.get("highEdge", 1.0)), int(float(b.get("count", 0)))) for b in bins]
        except (TypeError, ValueError):
            return 0.0
        total = sum(c for _, c in counts)
        if total == 0:
            return 0.0
        bare = sum(c for high_edge, c in counts if high_edge <= BARE_NDVI_THRESHOLD)
        return bare / total

    def detect_change(self, lat: float, lon: float) -> ChangeDetectionOutcome:
        now = datetime.now(timezone.utc)
        baseline_from = now - timedelta(days=BASELINE_DAYS_AGO[0])
        baseline_to = now - timedelta(days=BASELINE_DAYS_AGO[1])
        current_from = now - timedelta(days=CURRENT_DAYS_AGO[0])
        current_to = now

        self._get_token()  # fetch once up front so the two parallel calls share it
        with ThreadPoolExecutor(max_workers=2) as pool:
            baseline_future = pool.submit(self._query_window, lat, lon, baseline_from, baseline_to)
            current_future = pool.submit(self._query_window, lat, lon, current_from, current_to)
            baseline_json = baseline_future.result()
            current_json = current_future.result()

        baseline_stats = self._extract_band_stats(baseline_json)
        current_stats = self._extract_band_stats(current_json)

        def cloud_pct(stats: dict | None) -> float:
            if not stats:
                return 100.0
            return round((1 - stats["_valid_fraction"]) * 100, 1)

        baseline_window_days = (baseline_to - baseline_from).days
        current_window_days = (current_to - current_from).days

        previous_obs = ObservationResult(
            provider=f"Sentinel-2 L2A (Sentinel Hub, {baseline_window_days}-day window, least-cloud mosaic)",
            acquisition_date=baseline_to,
            resolution_m=10.0,
            cloud_coverage_pct=cloud_pct(baseline_stats),
            is_simulated=False,
        )
        current_obs = ObservationResult(
            provider=f"Sentinel-2 L2A (Sentinel Hub, {current_window_days}-day window, least-cloud mosaic)",
            acquisition_date=current_to,
            resolution_m=10.0,
            cloud_coverage_pct=cloud_pct(current_stats),
            is_simulated=False,
        )

        if baseline_stats is None or current_stats is None:
            raise SatelliteProviderError(
                "No usable cloud-free Sentinel-2 imagery was found for this AOI in the analysis "
                "windows (too much cloud cover). Try a different location or wait for a clearer pass."
            )

        delta_mean = current_stats["mean"] - baseline_stats["mean"]

        if delta_mean > -NDVI_CHANGE_THRESHOLD:
            return ChangeDetectionOutcome(
                previous_observation=previous_obs, current_observation=current_obs, change_detected=False,
            )

        current_mean = current_stats["mean"]
        if current_mean < 0.15:
            detection_type = "EXPOSED_SOIL"
        elif delta_mean <= -0.3:
            detection_type = "EXCAVATION"
        elif delta_mean <= -0.18:
            detection_type = "PIT_EXPANSION"
        else:
            detection_type = "VEGETATION_LOSS"

        confidence = round(min(0.55 + abs(delta_mean), 0.96), 2)

        baseline_bare = self._bare_fraction(baseline_stats)
        current_bare = self._bare_fraction(current_stats)
        delta_bare_fraction = max(current_bare - baseline_bare, 0.0)
        aoi_hectares = _aoi_area_hectares(lat, AOI_HALF_SIZE_DEG)
        area_hectares = round(delta_bare_fraction * aoi_hectares, 1)
        if area_hectares <= 0:
            # Histogram didn't show a clean bare-pixel increase even though the
            # mean dropped - fall back to a conservative estimate from the mean delta.
            area_hectares = round(min(abs(delta_mean), 1.0) * aoi_hectares * 0.5, 1)

        return ChangeDetectionOutcome(
            previous_observation=previous_obs,
            current_observation=current_obs,
            change_detected=True,
            detection_type=detection_type,
            confidence=confidence,
            estimated_area_hectares=area_hectares,
        )
