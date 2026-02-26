"""
Service: Compliance Checker
Multi-standard regulatory compliance assessment (WHO, CPCB, NAAQS).
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from app.config import settings

WHO_LIMITS = {
    "pm25": {"limit": settings.who_pm25_24h, "period": "24h", "unit": "µg/m³"},
    "pm10": {"limit": settings.who_pm10_24h, "period": "24h", "unit": "µg/m³"},
    "no2":  {"limit": settings.who_no2_24h,  "period": "24h", "unit": "µg/m³"},
    "o3":   {"limit": settings.who_o3_8h,   "period": "8h",  "unit": "µg/m³"},
}

CPCB_LIMITS = {
    "pm25": {"limit": settings.cpcb_pm25_24h, "period": "24h", "unit": "µg/m³"},
    "pm10": {"limit": settings.cpcb_pm10_24h, "period": "24h", "unit": "µg/m³"},
    "no2":  {"limit": settings.cpcb_no2_24h,  "period": "24h", "unit": "µg/m³"},
    "o3":   {"limit": settings.cpcb_o3_8h,   "period": "8h",  "unit": "µg/m³"},
    "co":   {"limit": settings.cpcb_co_8h,   "period": "8h",  "unit": "mg/m³"},
    "so2":  {"limit": settings.cpcb_so2_24h,  "period": "24h", "unit": "µg/m³"},
}

# US NAAQS 2023 Primary Standards (approximated µg/m³)
NAAQS_LIMITS = {
    "pm25": {"limit": 35.0,  "period": "24h",  "unit": "µg/m³"},
    "pm10": {"limit": 150.0, "period": "24h",  "unit": "µg/m³"},
    "no2":  {"limit": 100.0, "period": "annual", "unit": "µg/m³"},
    "o3":   {"limit": 137.0, "period": "8h",   "unit": "µg/m³"},
    "co":   {"limit": 10.0,  "period": "8h",   "unit": "mg/m³"},
    "so2":  {"limit": 196.0, "period": "1h",   "unit": "µg/m³"},
}


def assess_compliance(
    pollutants: Dict[str, Optional[float]],
    location_id: int = 1,
    period_hours: int = 24,
) -> Dict[str, Any]:
    """
    Check pollutant averages against WHO, CPCB, and NAAQS standards.
    Returns a structured compliance report.
    """
    violations: List[Dict] = []
    standards_checked = {"WHO": WHO_LIMITS, "CPCB": CPCB_LIMITS, "NAAQS": NAAQS_LIMITS}
    compliance_map: Dict[str, bool] = {"WHO": True, "CPCB": True, "NAAQS": True}

    for standard_name, limits in standards_checked.items():
        for pollutant, info in limits.items():
            value = pollutants.get(pollutant)
            if value is None:
                continue
            if value > info["limit"]:
                exceeded_pct = round(((value - info["limit"]) / info["limit"]) * 100, 2)
                violations.append({
                    "pollutant": pollutant.upper(),
                    "standard": standard_name,
                    "measured": round(value, 3),
                    "threshold": info["limit"],
                    "exceeded_by_pct": exceeded_pct,
                    "unit": info["unit"],
                    "period": info["period"],
                })
                compliance_map[standard_name] = False

    # Compute a compliance score (0–100)
    total_checks = sum(len(lim) for lim in standards_checked.values())
    total_violations = len(violations)
    score = round(max(0, 100 - (total_violations / max(total_checks, 1)) * 100), 2)

    # Risk level based on score
    risk_level = (
        "Critical" if score < 30 else
        "High" if score < 50 else
        "Moderate" if score < 75 else
        "Low" if score < 90 else
        "Compliant"
    )

    # Organize stats by standard for the frontend
    standards = {}
    for std_name, limits in standards_checked.items():
        pollutants_detail = {}
        passed_count = 0
        total_std_checks = len(limits)
        
        for pol, info in limits.items():
            val = pollutants.get(pol)
            compliant = val is None or val <= info["limit"]
            if compliant:
                passed_count += 1
            
            pollutants_detail[pol] = {
                "value": round(val, 2) if val is not None else 0,
                "limit": info["limit"],
                "unit": info["unit"],
                "compliant": compliant,
                "exceedance_pct": round(((val - info["limit"]) / info["limit"]) * 100, 2) if val and val > info["limit"] else 0
            }
        
        standards[std_name] = {
            "pollutants": pollutants_detail,
            "score": round((passed_count / total_std_checks) * 100, 2),
            "passed": compliance_map[std_name]
        }

    # Technical recommendations
    recommendations = []
    if score < 90:
        recommendations.append("Enhance filtration systems for PM2.5/PM10 mitigation.")
    if not compliance_map["WHO"]:
        recommendations.append("Update local emission targets to align with WHO 2021 air quality guidelines.")
    if any(v["pollutant"] == "NO2" for v in violations):
        recommendations.append("Implement traffic restriction zones (LEZs) to reduce NOx concentrations.")
    if not recommendations:
        recommendations.append("Maintain current environmental controls and periodic audit schedule.")

    return {
        "location_id": location_id,
        "assessed_at": datetime.utcnow(),
        "period_hours": period_hours,
        "overall_compliance": score >= 100,
        "standards": standards,
        "risk_level": risk_level,
        "recommendations": recommendations,
        "narrative": _generate_narrative(violations, compliance_map, score),
        "violations": violations, # Keep for backward compatibility if any
    }


def _generate_narrative(violations, compliance_map, score) -> str:
    if not violations:
        return "All monitored pollutants are within WHO, CPCB, and NAAQS permissible limits. Air quality is compliant."
    parts = []
    failed = [s for s, c in compliance_map.items() if not c]
    parts.append(f"Non-compliant with {', '.join(failed)} standards (score: {score}/100).")
    pollutants_exceeded = list({v["pollutant"] for v in violations})
    parts.append(f"Exceedances detected: {', '.join(pollutants_exceeded)}.")
    worst = max(violations, key=lambda x: x["exceeded_by_pct"])
    parts.append(
        f"Highest exceedance: {worst['pollutant']} exceeds {worst['standard']} limit "
        f"by {worst['exceeded_by_pct']}%."
    )
    return " ".join(parts)
