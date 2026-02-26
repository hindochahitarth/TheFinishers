"""
ORM Model: Sensor Reading — raw & processed environmental data
"""

from datetime import datetime
from sqlalchemy import (
    String, Float, Integer, DateTime, ForeignKey,
    Boolean, Text, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.database import Base


class AQICategory(str, enum.Enum):
    GOOD = "Good"
    SATISFACTORY = "Satisfactory"
    MODERATE = "Moderate"
    POOR = "Poor"
    VERY_POOR = "Very Poor"
    SEVERE = "Severe"
    UNKNOWN = "Unknown"


class DataSource(str, enum.Enum):
    OPENAQ = "OpenAQ"
    OPENWEATHER = "OpenWeatherMap"
    TOMTOM = "TomTom"
    SIMULATED = "Simulated"
    MANUAL = "Manual"


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # ── Air Quality Pollutants (µg/m³ unless noted) ───────
    pm25: Mapped[float] = mapped_column(Float, nullable=True)     # PM2.5
    pm10: Mapped[float] = mapped_column(Float, nullable=True)     # PM10
    no2: Mapped[float] = mapped_column(Float, nullable=True)      # NO2
    o3: Mapped[float] = mapped_column(Float, nullable=True)       # Ozone
    co: Mapped[float] = mapped_column(Float, nullable=True)       # CO (mg/m³)
    so2: Mapped[float] = mapped_column(Float, nullable=True)      # SO2
    nh3: Mapped[float] = mapped_column(Float, nullable=True)      # Ammonia
    no: Mapped[float] = mapped_column(Float, nullable=True)       # Nitric oxide

    # ── Computed AQI ─────────────────────────────────────
    aqi: Mapped[float] = mapped_column(Float, nullable=True)
    aqi_category: Mapped[str] = mapped_column(
        SQLEnum(AQICategory), default=AQICategory.UNKNOWN, nullable=True
    )
    dominant_pollutant: Mapped[str] = mapped_column(String(20), nullable=True)

    # ── Weather ─────────────────────────────────────────
    temperature: Mapped[float] = mapped_column(Float, nullable=True)     # °C
    humidity: Mapped[float] = mapped_column(Float, nullable=True)        # %
    wind_speed: Mapped[float] = mapped_column(Float, nullable=True)      # m/s
    wind_direction: Mapped[float] = mapped_column(Float, nullable=True)  # degrees
    pressure: Mapped[float] = mapped_column(Float, nullable=True)        # hPa
    visibility: Mapped[float] = mapped_column(Float, nullable=True)      # km
    uv_index: Mapped[float] = mapped_column(Float, nullable=True)
    cloud_cover: Mapped[float] = mapped_column(Float, nullable=True)     # %
    precipitation: Mapped[float] = mapped_column(Float, nullable=True)   # mm/h
    weather_condition: Mapped[str] = mapped_column(String(100), nullable=True)

    # ── Traffic ─────────────────────────────────────────
    traffic_density_index: Mapped[float] = mapped_column(Float, nullable=True)  # 0-10
    congestion_level: Mapped[str] = mapped_column(String(50), nullable=True)
    average_speed_kmh: Mapped[float] = mapped_column(Float, nullable=True)

    # ── Rolling Features (pre-computed) ─────────────────
    pm25_1h_avg: Mapped[float] = mapped_column(Float, nullable=True)
    pm25_24h_avg: Mapped[float] = mapped_column(Float, nullable=True)
    aqi_1h_avg: Mapped[float] = mapped_column(Float, nullable=True)
    aqi_24h_avg: Mapped[float] = mapped_column(Float, nullable=True)

    # ── Data Quality ────────────────────────────────────
    source: Mapped[str] = mapped_column(SQLEnum(DataSource), default=DataSource.OPENAQ)
    data_quality_score: Mapped[float] = mapped_column(Float, default=1.0)  # 0–1
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=True)
    is_imputed: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_payload: Mapped[str] = mapped_column(Text, nullable=True)  # JSON blob

    # ── Relationships ───────────────────────────────────
    location = relationship("Location", back_populates="sensor_readings")

    def __repr__(self):
        return (
            f"<SensorReading location_id={self.location_id} "
            f"ts='{self.timestamp}' aqi={self.aqi} cat='{self.aqi_category}'>"
        )
