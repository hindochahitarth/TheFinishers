"""
ORM Model: ML Model Registry
Tracks versioned ML models with performance metrics.
"""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Float, Boolean, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_type: Mapped[str] = mapped_column(String(100), nullable=False)  # xgboost/lstm/isolation_forest
    task: Mapped[str] = mapped_column(String(100), nullable=False)         # aqi_forecast/anomaly_detect
    artifact_path: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Training metadata
    trained_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    training_data_start: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    training_data_end: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    n_training_samples: Mapped[int] = mapped_column(Integer, nullable=True)
    features_used: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Performance metrics
    rmse: Mapped[float] = mapped_column(Float, nullable=True)
    mae: Mapped[float] = mapped_column(Float, nullable=True)
    r2: Mapped[float] = mapped_column(Float, nullable=True)
    mape: Mapped[float] = mapped_column(Float, nullable=True)
    f1_score: Mapped[float] = mapped_column(Float, nullable=True)     # For classification tasks
    roc_auc: Mapped[float] = mapped_column(Float, nullable=True)
    additional_metrics: Mapped[dict] = mapped_column(JSON, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_production: Mapped[bool] = mapped_column(Boolean, default=False)
    deployment_notes: Mapped[str] = mapped_column(Text, nullable=True)

    def __repr__(self):
        return f"<ModelRegistry name='{self.name}' version='{self.version}' active={self.is_active}>"
