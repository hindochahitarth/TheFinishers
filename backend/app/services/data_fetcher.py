"""
Service: External Data Fetcher
Async HTTP clients for OpenWeatherMap, OpenAQ, and TomTom Traffic APIs.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import httpx
from app.config import settings

logger = logging.getLogger(__name__)

OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"
OPENAQ_BASE = "https://api.openaq.org/v2"
TOMTOM_BASE = "https://api.tomtom.com/traffic/services/4"

DEFAULT_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


async def fetch_weather(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Fetch current weather from OpenWeatherMap."""
    if not settings.openweather_api_key or settings.openweather_api_key.startswith("your_"):
        logger.warning("OpenWeatherMap API key not configured — using mock data")
        return _mock_weather(lat, lon)

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(
                f"{OPENWEATHER_BASE}/weather",
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": settings.openweather_api_key,
                    "units": "metric",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "temperature": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "pressure": data["main"]["pressure"],
                "wind_speed": data["wind"]["speed"],
                "wind_direction": data["wind"].get("deg", 0),
                "visibility": data.get("visibility", 10000) / 1000,
                "cloud_cover": data["clouds"]["all"],
                "weather_condition": data["weather"][0]["description"].title() if data.get("weather") else None,
                "uv_index": None,
                "precipitation": data.get("rain", {}).get("1h", 0.0),
            }
    except Exception as e:
        logger.error(f"OpenWeatherMap fetch failed: {e}")
        return _mock_weather(lat, lon)


async def fetch_air_quality(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Fetch air quality from OpenAQ v2 nearest sensor."""
    if not settings.openaq_api_key or settings.openaq_api_key.startswith("your_"):
        logger.warning("OpenAQ API key not configured — using mock data")
        return _mock_air_quality()

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(
                f"{OPENAQ_BASE}/measurements",
                headers={"X-API-Key": settings.openaq_api_key},
                params={
                    "coordinates": f"{lat},{lon}",
                    "radius": 25000,  # 25 km
                    "limit": 50,
                    "order_by": "datetime",
                    "sort": "desc",
                },
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            return _parse_openaq_results(results)
    except Exception as e:
        logger.error(f"OpenAQ fetch failed: {e}")
        return _mock_air_quality()


async def fetch_traffic(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Fetch traffic congestion from TomTom Traffic Flow API."""
    if not settings.tomtom_api_key or settings.tomtom_api_key.startswith("your_"):
        logger.warning("TomTom API key not configured — using mock data")
        return _mock_traffic()

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(
                f"{TOMTOM_BASE}/flowSegmentData/relative0/10/json",
                params={
                    "key": settings.tomtom_api_key,
                    "point": f"{lat},{lon}",
                    "unit": "KMPH",
                },
            )
            resp.raise_for_status()
            data = resp.json().get("flowSegmentData", {})
            current_speed = data.get("currentSpeed", 30)
            free_flow = data.get("freeFlowSpeed", 50)
            ratio = current_speed / max(free_flow, 1)
            density_index = round((1 - ratio) * 10, 2)
            level = (
                "Free Flow" if ratio > 0.8 else
                "Light" if ratio > 0.6 else
                "Moderate" if ratio > 0.4 else
                "Heavy" if ratio > 0.2 else "Standstill"
            )
            return {
                "traffic_density_index": density_index,
                "congestion_level": level,
                "average_speed_kmh": current_speed,
            }
    except Exception as e:
        logger.error(f"TomTom fetch failed: {e}")
        return _mock_traffic()


# ── Parsers ──────────────────────────────────────────────────────────────────
def _parse_openaq_results(results: list) -> Dict[str, Any]:
    """Aggregate OpenAQ measurements into a flat pollutant dict."""
    param_map = {"pm25": None, "pm10": None, "no2": None, "o3": None, "co": None, "so2": None, "nh3": None}
    for r in results:
        param = r.get("parameter", "").lower().replace(".", "")
        if param in param_map and param_map[param] is None:
            param_map[param] = r.get("value")
    return param_map


# ── Mock Data (when API keys not configured) ─────────────────────────────────
import random
import math

def _mock_weather(lat: float, lon: float) -> Dict[str, Any]:
    """Realistic mock weather for New Delhi climate."""
    hour = datetime.now(timezone.utc).hour
    base_temp = 22 + 8 * math.sin((hour - 6) * math.pi / 12)
    return {
        "temperature": round(base_temp + random.uniform(-2, 2), 1),
        "humidity": round(random.uniform(40, 75), 1),
        "pressure": round(random.uniform(1008, 1020), 1),
        "wind_speed": round(random.uniform(1, 8), 1),
        "wind_direction": round(random.uniform(0, 360), 0),
        "visibility": round(random.uniform(3, 15), 1),
        "cloud_cover": round(random.uniform(10, 60), 0),
        "weather_condition": random.choice(["Haze", "Clear Sky", "Partly Cloudy", "Mist"]),
        "uv_index": round(max(0, 5 * math.sin((hour - 8) * math.pi / 10)), 1),
        "precipitation": 0.0,
    }

def _mock_air_quality() -> Dict[str, Any]:
    """Realistic mock AQ for Delhi-level pollution."""
    hour = datetime.now(timezone.utc).hour
    # Morning/evening rush hour peaks
    rush = 1.4 if 7 <= hour <= 10 or 17 <= hour <= 21 else 1.0
    return {
        "pm25": round(random.uniform(45, 130) * rush, 2),
        "pm10": round(random.uniform(80, 220) * rush, 2),
        "no2": round(random.uniform(30, 95) * rush, 2),
        "o3": round(random.uniform(20, 70), 2),
        "co": round(random.uniform(0.5, 3.5) * rush, 2),
        "so2": round(random.uniform(10, 55), 2),
        "nh3": round(random.uniform(5, 30), 2),
    }

def _mock_traffic() -> Dict[str, Any]:
    """Mock traffic based on time of day."""
    hour = datetime.now(timezone.utc).hour + 5  # IST offset
    rush = hour in range(8, 11) or hour in range(18, 22)
    index = round(random.uniform(6, 9) if rush else random.uniform(2, 5), 1)
    speed = round(random.uniform(10, 25) if rush else random.uniform(30, 55), 1)
    level = "Heavy" if rush else "Moderate"
    return {"traffic_density_index": index, "congestion_level": level, "average_speed_kmh": speed}
