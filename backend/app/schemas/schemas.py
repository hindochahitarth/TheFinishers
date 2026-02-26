"""
Pydantic Schemas — Environmental Monitoring API
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ── Location ──────────────────────────────────────────────────────────────────
class LocationBase(BaseModel):
    name: str
    city: str
    state: Optional[str] = None
    country: str = "India"
    country_code: str = "IN"
    latitude: float
    longitude: float
    timezone: str = "Asia/Kolkata"

class LocationCreate(LocationBase):
    station_id: Optional[str] = None

class LocationOut(LocationBase):
    id: int
    station_id: Optional[str]
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Sensor Reading ────────────────────────────────────────────────────────────
class PollutantData(BaseModel):
    pm25: Optional[float] = Field(None, description="PM2.5 in µg/m³")
    pm10: Optional[float] = Field(None, description="PM10 in µg/m³")
    no2: Optional[float] = Field(None, description="NO₂ in µg/m³")
    o3: Optional[float] = Field(None, description="O₃ in µg/m³")
    co: Optional[float] = Field(None, description="CO in mg/m³")
    so2: Optional[float] = Field(None, description="SO₂ in µg/m³")
    nh3: Optional[float] = Field(None, description="NH₃ in µg/m³")


class WeatherData(BaseModel):
    temperature: Optional[float] = Field(None, description="Temperature in °C")
    humidity: Optional[float] = Field(None, description="Relative humidity %")
    wind_speed: Optional[float] = Field(None, description="Wind speed m/s")
    wind_direction: Optional[float] = Field(None, description="Wind direction degrees")
    pressure: Optional[float] = Field(None, description="Atmospheric pressure hPa")
    visibility: Optional[float] = Field(None, description="Visibility km")
    uv_index: Optional[float] = None
    cloud_cover: Optional[float] = None
    precipitation: Optional[float] = None
    weather_condition: Optional[str] = None


class TrafficData(BaseModel):
    traffic_density_index: Optional[float] = Field(None, description="0–10 congestion index")
    congestion_level: Optional[str] = None
    average_speed_kmh: Optional[float] = None


class SensorReadingOut(BaseModel):
    id: int
    location_id: int
    timestamp: datetime
    aqi: Optional[float]
    aqi_category: Optional[str]
    dominant_pollutant: Optional[str]
    pollutants: PollutantData
    weather: WeatherData
    traffic: TrafficData
    is_anomaly: bool
    anomaly_score: Optional[float]
    data_quality_score: float
    source: str
    model_config = {"from_attributes": True}


class CurrentConditionsResponse(BaseModel):
    location: LocationOut
    reading: SensorReadingOut
    alert_count: int
    compliance_status: str
    retrieved_at: datetime


class HistoryResponse(BaseModel):
    location_id: int
    readings: List[SensorReadingOut]
    total: int
    from_dt: datetime
    to_dt: datetime


# ── Alert ─────────────────────────────────────────────────────────────────────
class AlertOut(BaseModel):
    id: int
    location_id: int
    title: str
    message: str
    pollutant: Optional[str]
    measured_value: Optional[float]
    threshold_value: Optional[float]
    threshold_standard: Optional[str]
    severity: str
    status: str
    is_anomaly_based: bool
    root_cause_summary: Optional[str]
    triggered_at: datetime
    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    alerts: List[AlertOut]
    total: int
    active_count: int


# ── Compliance ────────────────────────────────────────────────────────────────
class ViolationItem(BaseModel):
    pollutant: str
    standard: str
    measured: float
    threshold: float
    exceeded_by_pct: float
    unit: str


class ComplianceResponse(BaseModel):
    location_id: int
    assessed_at: datetime
    period_hours: int
    who_compliant: Optional[bool]
    cpcb_compliant: Optional[bool]
    naaqs_compliant: Optional[bool]
    overall_compliance_score: Optional[float]
    risk_level: Optional[str]
    violations: List[ViolationItem]
    narrative: Optional[str]
    model_config = {"from_attributes": True}


# ── Forecast ──────────────────────────────────────────────────────────────────
class ForecastPoint(BaseModel):
    timestamp: datetime
    aqi_predicted: float
    aqi_lower: float
    aqi_upper: float
    aqi_category: str
    pm25_predicted: Optional[float] = None
    no2_predicted: Optional[float] = None
    confidence: float


class ForecastResponse(BaseModel):
    location_id: int
    generated_at: datetime
    horizon_hours: int
    model_name: str
    model_version: str
    forecast: List[ForecastPoint]
    feature_importance: Optional[dict] = None


# ── Agent ─────────────────────────────────────────────────────────────────────
class AgentQueryRequest(BaseModel):
    query: str = Field(..., description="Natural language environmental question")
    session_id: Optional[str] = Field(None, description="Conversation session ID")
    location_id: Optional[int] = None


class AgentQueryResponse(BaseModel):
    session_id: str
    query: str
    response: str
    reasoning_trace: Optional[List[dict]] = None
    tools_used: Optional[List[str]] = None
    latency_ms: float
    model: str


# ── Recommendation ────────────────────────────────────────────────────────────
class RecommendationOut(BaseModel):
    id: int
    category: str
    priority: str
    title: str
    description: str
    action_steps: Optional[list]
    affected_population: Optional[str]
    expected_impact: Optional[str]
    time_horizon: Optional[str]
    confidence_score: Optional[float]
    created_at: datetime
    model_config = {"from_attributes": True}


class RecommendationListResponse(BaseModel):
    recommendations: List[RecommendationOut]
    total: int
    location_id: Optional[int]
