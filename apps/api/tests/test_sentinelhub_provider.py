"""Unit tests for SentinelHubProvider's response parsing, covering quirks
found while testing against the real Sentinel Hub / CDSE Statistical API:
numeric stats fields coming back as strings, and legitimate NaN means when
sampleCount > 0. No network access - these construct response dicts directly."""

from app.services.satellite.sentinelhub_provider import SentinelHubProvider


def _response(mean, sample_count, no_data_count, bins=None):
    return {
        "data": [{
            "outputs": {"ndvi": {"bands": {"B0": {
                "stats": {
                    "mean": mean, "min": mean, "max": mean, "stDev": "0.1",
                    "sampleCount": sample_count, "noDataCount": no_data_count,
                },
                "histogram": {"bins": bins or []},
            }}}}
        }]
    }


def test_extract_band_stats_coerces_string_numbers():
    resp = _response(mean="0.42", sample_count=10000, no_data_count=100)
    stats = SentinelHubProvider._extract_band_stats(resp)
    assert stats is not None
    assert stats["mean"] == 0.42
    assert isinstance(stats["sampleCount"], int)


def test_extract_band_stats_rejects_nan_mean_even_with_samples():
    """Real API quirk: sampleCount can be > 0 while mean is 'NaN' (e.g. a
    single-scene mosaic that turned out fully cloud-masked)."""
    resp = _response(mean="NaN", sample_count=10000, no_data_count=10000)
    stats = SentinelHubProvider._extract_band_stats(resp)
    assert stats is None


def test_extract_band_stats_rejects_zero_samples():
    resp = _response(mean="0.1", sample_count=0, no_data_count=0)
    stats = SentinelHubProvider._extract_band_stats(resp)
    assert stats is None


def test_extract_band_stats_rejects_mostly_cloudy_window():
    resp = _response(mean="0.1", sample_count=100, no_data_count=95)
    stats = SentinelHubProvider._extract_band_stats(resp)
    assert stats is None  # valid_fraction = 5% < MIN_VALID_SAMPLE_FRACTION


def test_bare_fraction_handles_string_histogram_counts():
    bins = [
        {"highEdge": 0.1, "count": "40"},
        {"highEdge": 0.5, "count": "60"},
    ]
    stats = {"_histogram": bins}
    fraction = SentinelHubProvider._bare_fraction(stats)
    assert fraction == 0.4  # only the first bin (highEdge <= 0.3) counts as bare
