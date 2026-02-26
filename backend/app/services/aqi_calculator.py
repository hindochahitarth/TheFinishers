"""
Service: AQI Calculator
Implements CPCB (India) and WHO breakpoints for AQI computation.
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import math


@dataclass
class AQIBreakpoint:
    c_low: float
    c_high: float
    i_low: int
    i_high: int


# CPCB AQI Breakpoints (India National Air Quality Index)
CPCB_PM25_BREAKPOINTS = [
    AQIBreakpoint(0.0, 30.0, 0, 50),
    AQIBreakpoint(30.0, 60.0, 51, 100),
    AQIBreakpoint(60.0, 90.0, 101, 200),
    AQIBreakpoint(90.0, 120.0, 201, 300),
    AQIBreakpoint(120.0, 250.0, 301, 400),
    AQIBreakpoint(250.0, 500.0, 401, 500),
]

CPCB_PM10_BREAKPOINTS = [
    AQIBreakpoint(0, 50, 0, 50),
    AQIBreakpoint(50, 100, 51, 100),
    AQIBreakpoint(100, 250, 101, 200),
    AQIBreakpoint(250, 350, 201, 300),
    AQIBreakpoint(350, 430, 301, 400),
    AQIBreakpoint(430, 600, 401, 500),
]

CPCB_NO2_BREAKPOINTS = [
    AQIBreakpoint(0, 40, 0, 50),
    AQIBreakpoint(40, 80, 51, 100),
    AQIBreakpoint(80, 180, 101, 200),
    AQIBreakpoint(180, 280, 201, 300),
    AQIBreakpoint(280, 400, 301, 400),
    AQIBreakpoint(400, 800, 401, 500),
]

CPCB_O3_BREAKPOINTS = [
    AQIBreakpoint(0, 50, 0, 50),
    AQIBreakpoint(50, 100, 51, 100),
    AQIBreakpoint(100, 168, 101, 200),
    AQIBreakpoint(168, 208, 201, 300),
    AQIBreakpoint(208, 748, 301, 400),
    AQIBreakpoint(748, 1000, 401, 500),
]

CPCB_CO_BREAKPOINTS = [   # mg/m³
    AQIBreakpoint(0.0, 1.0, 0, 50),
    AQIBreakpoint(1.0, 2.0, 51, 100),
    AQIBreakpoint(2.0, 10.0, 101, 200),
    AQIBreakpoint(10.0, 17.0, 201, 300),
    AQIBreakpoint(17.0, 34.0, 301, 400),
    AQIBreakpoint(34.0, 50.0, 401, 500),
]

CPCB_SO2_BREAKPOINTS = [
    AQIBreakpoint(0, 40, 0, 50),
    AQIBreakpoint(40, 80, 51, 100),
    AQIBreakpoint(80, 380, 101, 200),
    AQIBreakpoint(380, 800, 201, 300),
    AQIBreakpoint(800, 1600, 301, 400),
    AQIBreakpoint(1600, 2100, 401, 500),
]

AQI_CATEGORIES = [
    (0, 50, "Good"),
    (51, 100, "Satisfactory"),
    (101, 200, "Moderate"),
    (201, 300, "Poor"),
    (301, 400, "Very Poor"),
    (401, 500, "Severe"),
]

POLLUTANT_BREAKPOINTS = {
    "pm25": CPCB_PM25_BREAKPOINTS,
    "pm10": CPCB_PM10_BREAKPOINTS,
    "no2": CPCB_NO2_BREAKPOINTS,
    "o3": CPCB_O3_BREAKPOINTS,
    "co": CPCB_CO_BREAKPOINTS,
    "so2": CPCB_SO2_BREAKPOINTS,
}


def _sub_index(concentration: float, breakpoints: list[AQIBreakpoint]) -> Optional[float]:
    """Linear interpolation of AQI sub-index from concentration."""
    if concentration is None or math.isnan(concentration) or concentration < 0:
        return None
    for bp in breakpoints:
        if bp.c_low <= concentration <= bp.c_high:
            return ((bp.i_high - bp.i_low) / (bp.c_high - bp.c_low)) * (
                concentration - bp.c_low
            ) + bp.i_low
    # Above max breakpoint → cap at 500
    return 500.0


def compute_aqi(
    pm25: Optional[float] = None,
    pm10: Optional[float] = None,
    no2: Optional[float] = None,
    o3: Optional[float] = None,
    co: Optional[float] = None,
    so2: Optional[float] = None,
) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """
    Compute CPCB AQI from pollutant concentrations.
    Returns: (aqi_value, category_label, dominant_pollutant)
    """
    pollutants = {
        "pm25": pm25,
        "pm10": pm10,
        "no2": no2,
        "o3": o3,
        "co": co,
        "so2": so2,
    }

    sub_indices = {}
    for name, value in pollutants.items():
        if value is not None and not math.isnan(value):
            si = _sub_index(value, POLLUTANT_BREAKPOINTS[name])
            if si is not None:
                sub_indices[name] = si

    if not sub_indices:
        return None, "Unknown", None

    max_pollutant = max(sub_indices, key=sub_indices.get)
    aqi_value = sub_indices[max_pollutant]

    category = "Unknown"
    for low, high, label in AQI_CATEGORIES:
        if low <= aqi_value <= high:
            category = label
            break

    return round(aqi_value, 2), category, max_pollutant
