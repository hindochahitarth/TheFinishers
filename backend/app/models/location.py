"""
ORM Model: Location / Monitoring Station
"""

from datetime import datetime
from sqlalchemy import String, Float, Boolean, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="India")
    country_code: Mapped[str] = mapped_column(String(5), nullable=False, default="IN")
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata")
    station_id: Mapped[str] = mapped_column(String(100), nullable=True, unique=True)  # OpenAQ station ID
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sensor_readings = relationship("SensorReading", back_populates="location", lazy="dynamic")
    alerts = relationship("Alert", back_populates="location", lazy="dynamic")
    compliance_checks = relationship("ComplianceAssessment", back_populates="location", lazy="dynamic")

    def __repr__(self):
        return f"<Location id={self.id} name='{self.name}' city='{self.city}'>"
