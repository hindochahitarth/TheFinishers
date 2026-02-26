"""
ORM Model: Environmental Alert
"""

from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Boolean, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.database import Base


class AlertSeverity(str, enum.Enum):
    INFO = "Info"
    WARNING = "Warning"
    CRITICAL = "Critical"
    EMERGENCY = "Emergency"


class AlertStatus(str, enum.Enum):
    ACTIVE = "Active"
    ACKNOWLEDGED = "Acknowledged"
    RESOLVED = "Resolved"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    sensor_reading_id: Mapped[int] = mapped_column(Integer, ForeignKey("sensor_readings.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    pollutant: Mapped[str] = mapped_column(String(50), nullable=True)
    measured_value: Mapped[float] = mapped_column(Float, nullable=True)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=True)
    threshold_standard: Mapped[str] = mapped_column(String(50), nullable=True)  # WHO / CPCB / NAAQS
    severity: Mapped[str] = mapped_column(SQLEnum(AlertSeverity), default=AlertSeverity.WARNING)
    status: Mapped[str] = mapped_column(SQLEnum(AlertStatus), default=AlertStatus.ACTIVE)
    is_anomaly_based: Mapped[bool] = mapped_column(Boolean, default=False)
    root_cause_summary: Mapped[str] = mapped_column(Text, nullable=True)

    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    location = relationship("Location", back_populates="alerts")

    def __repr__(self):
        return f"<Alert id={self.id} severity='{self.severity}' pollutant='{self.pollutant}'>"
