"""
ORM Model: Compliance Assessment
Tracks regulatory compliance checks for WHO, CPCB, NAAQS standards.
"""

from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ComplianceAssessment(Base):
    __tablename__ = "compliance_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    assessed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    period_hours: Mapped[int] = mapped_column(Integer, default=24)  # assessment window

    # Per-standard compliance flags
    who_compliant: Mapped[bool] = mapped_column(Boolean, nullable=True)
    cpcb_compliant: Mapped[bool] = mapped_column(Boolean, nullable=True)
    naaqs_compliant: Mapped[bool] = mapped_column(Boolean, nullable=True)

    # Violations as JSON list of {pollutant, standard, measured, threshold, exceeded_by_pct}
    violations: Mapped[dict] = mapped_column(JSON, nullable=True)

    overall_compliance_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0–100
    risk_level: Mapped[str] = mapped_column(String(50), nullable=True)
    narrative: Mapped[str] = mapped_column(Text, nullable=True)  # LLM-generated explanation

    location = relationship("Location", back_populates="compliance_checks")

    def __repr__(self):
        return f"<ComplianceAssessment id={self.id} who={self.who_compliant} cpcb={self.cpcb_compliant}>"
