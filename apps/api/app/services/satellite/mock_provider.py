import random
from datetime import datetime, timedelta, timezone

from app.services.satellite.provider import ChangeDetectionResult, ObservationResult, SatelliteProvider

_DETECTION_WEIGHTS = [
    ("EXCAVATION", 3),
    ("EXPOSED_SOIL", 3),
    ("VEGETATION_LOSS", 3),
    ("PIT_EXPANSION", 2),
    ("NEW_ROAD", 1),
    ("WATER_SEDIMENTATION", 1),
]


class MockSatelliteProvider(SatelliteProvider):
    """Simulates a Sentinel-2-style before/after change-detection pass.

    Deterministic per (location, day): scanning the same AOI twice on the
    same day returns the same result, the way re-running analysis on the
    same pair of real scenes would. A new day produces a new pseudo-random
    draw, standing in for a new satellite pass becoming available.
    """

    name = "mock-satellite-change-detector"

    def detect_change(self, lat: float, lon: float) -> ChangeDetectionResult:
        today = datetime.now(timezone.utc).date().isoformat()
        seed = f"{round(lat, 3)}:{round(lon, 3)}:{today}"
        rng = random.Random(seed)

        types, weights = zip(*_DETECTION_WEIGHTS)
        detection_type = rng.choices(types, weights=weights, k=1)[0]
        confidence = round(rng.uniform(0.62, 0.94), 2)
        area_hectares = round(rng.uniform(1.5, 22.0), 1)

        now = datetime.now(timezone.utc)
        previous = ObservationResult(
            provider="Sentinel-2 (simulated baseline pass)",
            acquisition_date=now - timedelta(days=rng.randint(20, 60)),
            resolution_m=10.0,
            cloud_coverage_pct=round(rng.uniform(0, 15), 1),
            is_simulated=True,
        )
        current = ObservationResult(
            provider="Sentinel-2 (simulated latest pass)",
            acquisition_date=now - timedelta(days=rng.randint(0, 4)),
            resolution_m=10.0,
            cloud_coverage_pct=round(rng.uniform(0, 15), 1),
            is_simulated=True,
        )

        return ChangeDetectionResult(
            detection_type=detection_type,
            confidence=confidence,
            estimated_area_hectares=area_hectares,
            previous_observation=previous,
            current_observation=current,
        )
