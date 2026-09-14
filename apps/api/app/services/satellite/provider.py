"""Pluggable satellite change-detection provider (spec section 6/7).

`get_satellite_provider()` returns `MockSatelliteProvider` unconditionally
today - there is no real Sentinel Hub / Google Earth Engine integration in
this build (no credentials to connect to one). A real provider fetching
actual before/after scenes and running genuine change detection can be
dropped in later by implementing this same interface; nothing else in the
codebase needs to change, since the API route, the AIDetection persistence,
and the risk engine all operate on the interface's output shape, not on how
it was produced.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache


@dataclass
class ObservationResult:
    provider: str
    acquisition_date: datetime
    resolution_m: float
    cloud_coverage_pct: float
    is_simulated: bool


@dataclass
class ChangeDetectionResult:
    detection_type: str
    confidence: float
    estimated_area_hectares: float
    previous_observation: ObservationResult
    current_observation: ObservationResult


class SatelliteProvider(ABC):
    name: str

    @abstractmethod
    def detect_change(self, lat: float, lon: float) -> ChangeDetectionResult: ...


@lru_cache
def get_satellite_provider() -> SatelliteProvider:
    from app.services.satellite.mock_provider import MockSatelliteProvider

    return MockSatelliteProvider()
