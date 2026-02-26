"""
Service: Alert Engine
Threshold-based alert generation using WHO and CPCB standards.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from app.config import settings


# ── Threshold Configuration ───────────────────────────────────────────────────
WHO_THRESHOLDS = {
    "pm25": {"24h": settings.who_pm25_24h, "unit": "µg/m³"},
    "pm10": {"24h": settings.who_pm10_24h, "unit": "µg/m³"},
    "no2": {"24h": settings.who_no2_24h, "unit": "µg/m³"},
    "o3": {"8h": settings.who_o3_8h, "unit": "µg/m³"},
}

CPCB_THRESHOLDS = {
    "pm25": {"24h": settings.cpcb_pm25_24h, "unit": "µg/m³"},
    "pm10": {"24h": settings.cpcb_pm10_24h, "unit": "µg/m³"},
    "no2": {"24h": settings.cpcb_no2_24h, "unit": "µg/m³"},
    "o3": {"8h": settings.cpcb_o3_8h, "unit": "µg/m³"},
    "co": {"8h": settings.cpcb_co_8h, "unit": "mg/m³"},
    "so2": {"24h": settings.cpcb_so2_24h, "unit": "µg/m³"},
}

# AQI-based emergency thresholds
AQI_EMERGENCY_THRESHOLD = 300
AQI_CRITICAL_THRESHOLD = 200
AQI_WARNING_THRESHOLD = 100

# Severity classification by AQI
def classify_aqi_severity(aqi: float) -> str:
    if aqi >= AQI_EMERGENCY_THRESHOLD:
        return "Emergency"
    elif aqi >= AQI_CRITICAL_THRESHOLD:
        return "Critical"
    elif aqi >= AQI_WARNING_THRESHOLD:
        return "Warning"
    return "Info"


def check_pollutant_alerts(
    pollutants: Dict[str, Optional[float]],
    aqi: Optional[float] = None,
    location_id: int = 1,
) -> List[Dict[str, Any]]:
    """
    Check pollutant values against WHO and CPCB thresholds.
    Returns a list of alert dicts ready for DB insertion.
    """
    alerts = []
    now = datetime.utcnow()

    # AQI-level alert
    if aqi and aqi >= AQI_WARNING_THRESHOLD:
        severity = classify_aqi_severity(aqi)
        alerts.append({
            "location_id": location_id,
            "title": f"AQI {severity}: {aqi:.0f} — Air Quality Deteriorated",
            "message": (
                f"The Air Quality Index has reached {aqi:.0f}, classified as '{_aqi_category(aqi)}'. "
                f"Immediate attention may be required."
            ),
            "pollutant": "AQI",
            "measured_value": aqi,
            "threshold_value": AQI_WARNING_THRESHOLD,
            "threshold_standard": "CPCB",
            "severity": severity,
            "triggered_at": now,
        })

    # Per-pollutant checks against both WHO and CPCB
    for pollutant, value in pollutants.items():
        if value is None:
            continue

        for standard, thresholds in [("WHO", WHO_THRESHOLDS), ("CPCB", CPCB_THRESHOLDS)]:
            if pollutant not in thresholds:
                continue
            threshold_info = thresholds[pollutant]
            threshold_key = next(iter(threshold_info.keys() - {"unit"}))
            threshold_val = threshold_info[threshold_key]
            unit = threshold_info["unit"]

            if value > threshold_val:
                exceeded_pct = ((value - threshold_val) / threshold_val) * 100
                severity = "Emergency" if exceeded_pct > 150 else "Critical" if exceeded_pct > 50 else "Warning"
                alerts.append({
                    "location_id": location_id,
                    "title": f"{standard} {threshold_key.upper()} Exceeded: {pollutant.upper()} = {value:.1f} {unit}",
                    "message": (
                        f"{pollutant.upper()} concentration of {value:.2f} {unit} exceeds "
                        f"{standard} {threshold_key} threshold of {threshold_val} {unit} "
                        f"by {exceeded_pct:.1f}%."
                    ),
                    "pollutant": pollutant.upper(),
                    "measured_value": value,
                    "threshold_value": threshold_val,
                    "threshold_standard": standard,
                    "severity": severity,
                    "triggered_at": now,
                })

    return alerts


def _aqi_category(aqi: float) -> str:
    if aqi <= 50: return "Good"
    elif aqi <= 100: return "Satisfactory"
    elif aqi <= 200: return "Moderate"
    elif aqi <= 300: return "Poor"
    elif aqi <= 400: return "Very Poor"
    return "Severe"
