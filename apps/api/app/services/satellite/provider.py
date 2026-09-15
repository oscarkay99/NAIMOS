"""Pluggable satellite change-detection provider (spec section 6/7).

`get_satellite_provider()` returns `MockSatelliteProvider` by default, or
`SentinelHubProvider` once SENTINELHUB_CLIENT_ID/SECRET are configured - a
real Sentinel-2 NDVI-based change-detection pass via Sentinel Hub's
Statistical API. Nothing else in the codebase needs to change when the
provider is swapped: the API route, AIDetection persistence, and the risk
engine all operate on this interface's output shape, not on how it was
produced.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache


class SatelliteProviderError(Exception):
    """Raised when a real provider call fails (auth, API error, no usable
    imagery) - surfaced to the caller as a clear error rather than silently
    falling back to a fabricated result."""


@dataclass
class ObservationResult:
    provider: str
    acquisition_date: datetime
    resolution_m: float
    cloud_coverage_pct: float
    is_simulated: bool


@dataclass
class ChangeDetectionOutcome:
    previous_observation: ObservationResult
    current_observation: ObservationResult
    change_detected: bool
    detection_type: str | None = None
    confidence: float | None = None
    estimated_area_hectares: float | None = None


class SatelliteProvider(ABC):
    name: str
    is_simulated: bool

    @abstractmethod
    def detect_change(self, lat: float, lon: float) -> ChangeDetectionOutcome:
        """Always returns observation metadata for the AOI/windows checked.
        `change_detected=False` means the imagery was analyzed but nothing
        crossed the significance threshold - a real detector must be able
        to report "clean", not just always produce a finding."""
        ...


@lru_cache
def get_satellite_provider() -> SatelliteProvider:
    from app.core.config import get_settings

    settings = get_settings()
    if settings.sentinelhub_configured:
        from app.services.satellite.sentinelhub_provider import SentinelHubProvider

        return SentinelHubProvider()

    from app.services.satellite.mock_provider import MockSatelliteProvider

    return MockSatelliteProvider()
