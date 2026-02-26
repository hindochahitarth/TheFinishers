"""
Service: Recommendation Engine
Context-aware environmental action recommendations.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

HEALTH_RECS = {
    "Good": [],
    "Satisfactory": [
        {"title": "Outdoor Activities: Safe", "desc": "Air quality is satisfactory. Sensitive individuals may wish to limit prolonged outdoor exertion.", "priority": "Low", "category": "health"},
    ],
    "Moderate": [
        {"title": "Sensitive Groups: Reduce Outdoor Time", "desc": "Children, elderly, and those with respiratory/heart conditions should reduce prolonged outdoor exertion.", "priority": "Medium", "category": "health"},
        {"title": "Wear N95 Masks", "desc": "If outdoor exposure is unavoidable, wear N95/FFP2 masks for protection.", "priority": "Medium", "category": "health"},
    ],
    "Poor": [
        {"title": "Avoid Outdoor Activity", "desc": "Everyone should avoid prolonged outdoor physical activity. Move exercise indoors.", "priority": "High", "category": "health"},
        {"title": "Close Windows and Doors", "desc": "Keep windows closed to prevent polluted air from entering buildings. Use air purifiers if available.", "priority": "High", "category": "health"},
        {"title": "Health Check for Vulnerable Groups", "desc": "Monitor breathing, heart rate, and symptoms for elderly, children, and those with chronic illnesses.", "priority": "High", "category": "health"},
    ],
    "Very Poor": [
        {"title": "Stay Indoors — Air Quality Emergency", "desc": "The air quality has reached Very Poor levels. All residents should remain indoors with windows sealed.", "priority": "Urgent", "category": "health"},
        {"title": "Emergency Medical Preparedness", "desc": "Ensure rescue inhalers and emergency medications are readily accessible. Alert local health facilities.", "priority": "Urgent", "category": "health"},
        {"title": "School and Office Closures Advised", "desc": "Consider issuing advisories to close schools and outdoor venues until conditions improve.", "priority": "Urgent", "category": "policy"},
    ],
    "Severe": [
        {"title": "🚨 Severe Air Quality Emergency", "desc": "SEVERE air quality conditions. Avoid ALL outdoor activity. Emergency response protocols should be activated.", "priority": "Urgent", "category": "health"},
        {"title": "Activate Emergency Response Protocol", "desc": "Alert emergency services, issue public health emergency notices, and coordinate with hospitals.", "priority": "Urgent", "category": "policy"},
        {"title": "Industrial Emission Shutdown Order", "desc": "Coordinate with regulatory bodies to halt non-essential industrial activities contributing to pollution.", "priority": "Urgent", "category": "industrial"},
    ],
}

TRAFFIC_RECS = [
    {"title": "Promote Work-From-Home", "desc": "High traffic congestion is contributing to elevated NO2 and CO levels. Organizations should enable remote work.", "priority": "Medium", "category": "traffic"},
    {"title": "Optimize Traffic Signal Timing", "desc": "Adaptive traffic signal control can reduce vehicle idling by up to 20%, lowering emissions.", "priority": "Medium", "category": "traffic"},
    {"title": "Promote Public Transport Use", "desc": "Encourage commuters to use metro, bus, or carpooling to reduce vehicle density on major corridors.", "priority": "High", "category": "traffic"},
]

POLLUTANT_RECS = {
    "pm25": {"title": "PM2.5 Exceedance: Reduce Combustion Sources", "desc": "High fine particle pollution often driven by vehicle exhaust, open burning, or industrial sources. Enforce anti-burning regulations.", "priority": "High", "category": "industrial"},
    "no2": {"title": "NO₂ Alert: Traffic Emission Control", "desc": "Elevated NO2 is primarily from vehicular traffic. Implement odd-even vehicle schemes or low-emission zones.", "priority": "High", "category": "traffic"},
    "o3": {"title": "Ozone Alert: Limit VOC Emissions", "desc": "High ground-level ozone is driven by photochemical reactions. Limit VOC-emitting industrial processes during peak sunshine hours.", "priority": "Medium", "category": "industrial"},
    "so2": {"title": "SO₂ Alert: Industrial Source Check", "desc": "High SO2 levels indicate combustion of sulfur-rich fuels. Inspect nearby power plants and industrial facilities.", "priority": "High", "category": "industrial"},
    "co": {"title": "CO Alert: Combustion Monitoring", "desc": "Elevated CO from incomplete combustion. Check vehicular emission standards compliance and enforce idling restrictions.", "priority": "High", "category": "traffic"},
}


def generate_recommendations(
    aqi: Optional[float],
    aqi_category: str,
    dominant_pollutant: Optional[str],
    traffic_density_index: Optional[float],
    compliance_report: Optional[Dict] = None,
    location_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Generate context-aware recommendations from current environmental state."""
    recs = []
    now = datetime.utcnow()

    # Health-based recommendations
    category_recs = HEALTH_RECS.get(aqi_category, [])
    for rec in category_recs:
        recs.append({**rec, "created_at": now, "location_id": location_id, "confidence_score": 0.92,
                     "is_automated": True, "time_horizon": "immediate",
                     "affected_population": "General public, vulnerable groups",
                     "expected_impact": "Reduced health exposure to pollutants"})

    # Traffic recommendations if high congestion
    if traffic_density_index and traffic_density_index >= 6:
        for rec in TRAFFIC_RECS:
            recs.append({**rec, "created_at": now, "location_id": location_id, "confidence_score": 0.85,
                         "is_automated": True, "time_horizon": "short-term",
                         "affected_population": "Commuters and transport authorities",
                         "expected_impact": "10–20% reduction in vehicular emissions"})

    # Dominant pollutant recommendation
    if dominant_pollutant and dominant_pollutant.lower() in POLLUTANT_RECS:
        rec = POLLUTANT_RECS[dominant_pollutant.lower()]
        recs.append({**rec, "created_at": now, "location_id": location_id, "confidence_score": 0.88,
                     "is_automated": True, "time_horizon": "short-term",
                     "affected_population": "Regulatory bodies, industry",
                     "expected_impact": "Measurable reduction in dominant pollutant within 24–48h"})

    return recs
