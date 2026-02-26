"""
Continuous Learning Pipeline

Implements automated model retraining and performance monitoring.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
import pandas as pd
import numpy as np
import structlog
from dataclasses import dataclass
from enum import Enum

logger = structlog.get_logger(__name__)


class RetrainingTrigger(Enum):
    """Reasons for triggering model retraining."""
    SCHEDULED = "scheduled"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    DATA_DRIFT = "data_drift"
    MANUAL = "manual"
    NEW_DATA_THRESHOLD = "new_data_threshold"


@dataclass
class PerformanceMetrics:
    """Model performance metrics."""
    mae: float
    rmse: float
    mape: float
    r2: float
    timestamp: datetime
    
    def is_degraded(self, baseline: 'PerformanceMetrics', threshold: float = 0.2) -> bool:
        """Check if performance has degraded beyond threshold."""
        mae_change = (self.mae - baseline.mae) / (baseline.mae + 1e-6)
        rmse_change = (self.rmse - baseline.rmse) / (baseline.rmse + 1e-6)
        return mae_change > threshold or rmse_change > threshold


@dataclass
class DriftMetrics:
    """Data drift detection metrics."""
    feature_name: str
    mean_shift: float
    std_shift: float
    distribution_distance: float  # KL divergence or similar
    is_drifted: bool


class ContinuousLearningPipeline:
    """
    Manages continuous learning and model maintenance.
    
    Features:
    - Scheduled retraining
    - Performance monitoring
    - Data drift detection
    - Automatic model selection
    - A/B testing support
    """
    
    def __init__(
        self,
        model_trainer,
        data_preprocessor,
        min_samples_for_retrain: int = 500,
        performance_check_interval_hours: int = 6,
        drift_check_interval_hours: int = 24,
        auto_retrain: bool = True,
    ):
        """
        Initialize continuous learning pipeline.
        
        Args:
            model_trainer: ModelTrainer instance
            data_preprocessor: DataPreprocessor instance
            min_samples_for_retrain: Minimum new samples before retraining
            performance_check_interval_hours: How often to check performance
            drift_check_interval_hours: How often to check for data drift
            auto_retrain: Whether to automatically trigger retraining
        """
        self.model_trainer = model_trainer
        self.data_preprocessor = data_preprocessor
        self.min_samples = min_samples_for_retrain
        self.performance_interval = timedelta(hours=performance_check_interval_hours)
        self.drift_interval = timedelta(hours=drift_check_interval_hours)
        self.auto_retrain = auto_retrain
        
        self.baseline_performance: Optional[PerformanceMetrics] = None
        self.current_performance: Optional[PerformanceMetrics] = None
        self.training_data_stats: Dict[str, Dict] = {}
        self.retraining_history: List[Dict] = []
        
        self._running = False
        self._last_performance_check: Optional[datetime] = None
        self._last_drift_check: Optional[datetime] = None
        self._new_samples_count = 0
    
    def set_baseline(self, train_data: pd.DataFrame, metrics: PerformanceMetrics):
        """
        Set baseline performance from initial training.
        
        Args:
            train_data: Training data used
            metrics: Performance metrics from training
        """
        self.baseline_performance = metrics
        self.current_performance = metrics
        
        # Store training data statistics for drift detection
        numerical_cols = train_data.select_dtypes(include=[np.number]).columns
        for col in numerical_cols:
            self.training_data_stats[col] = {
                'mean': train_data[col].mean(),
                'std': train_data[col].std(),
                'min': train_data[col].min(),
                'max': train_data[col].max(),
                'median': train_data[col].median(),
            }
        
        logger.info(
            "Baseline set",
            mae=metrics.mae,
            rmse=metrics.rmse,
            tracked_features=len(self.training_data_stats),
        )
    
    def record_prediction(
        self,
        actual: float,
        predicted: float,
        features: Dict[str, float],
    ):
        """
        Record a prediction for performance monitoring.
        
        Args:
            actual: Actual observed value
            predicted: Model's prediction
            features: Feature values used for prediction
        """
        self._new_samples_count += 1
        
        # In production, store these in a buffer for batch evaluation
        pass
    
    def check_performance(
        self,
        recent_data: pd.DataFrame,
        predictions: np.ndarray,
        actuals: np.ndarray,
    ) -> PerformanceMetrics:
        """
        Evaluate model performance on recent data.
        
        Args:
            recent_data: Recent sensor readings
            predictions: Model predictions
            actuals: Actual values
            
        Returns:
            Current performance metrics
        """
        mae = float(np.mean(np.abs(actuals - predictions)))
        rmse = float(np.sqrt(np.mean((actuals - predictions) ** 2)))
        mape = float(np.mean(np.abs((actuals - predictions) / (actuals + 1)))) * 100
        
        # R-squared
        ss_res = np.sum((actuals - predictions) ** 2)
        ss_tot = np.sum((actuals - np.mean(actuals)) ** 2)
        r2 = float(1 - (ss_res / (ss_tot + 1e-10)))
        
        metrics = PerformanceMetrics(
            mae=mae,
            rmse=rmse,
            mape=mape,
            r2=r2,
            timestamp=datetime.utcnow(),
        )
        
        self.current_performance = metrics
        self._last_performance_check = datetime.utcnow()
        
        logger.info(
            "Performance checked",
            mae=mae,
            rmse=rmse,
            r2=r2,
        )
        
        return metrics
    
    def detect_data_drift(self, new_data: pd.DataFrame) -> List[DriftMetrics]:
        """
        Detect data drift in new data compared to training distribution.
        
        Args:
            new_data: New sensor readings
            
        Returns:
            List of drift metrics for each feature
        """
        drift_results = []
        
        for col, baseline_stats in self.training_data_stats.items():
            if col not in new_data.columns:
                continue
            
            new_mean = new_data[col].mean()
            new_std = new_data[col].std()
            
            # Compute shifts
            mean_shift = abs(new_mean - baseline_stats['mean']) / (baseline_stats['std'] + 1e-6)
            std_shift = abs(new_std - baseline_stats['std']) / (baseline_stats['std'] + 1e-6)
            
            # Simple distribution distance (normalized difference)
            dist = mean_shift + std_shift * 0.5
            
            # Drift threshold
            is_drifted = mean_shift > 0.5 or std_shift > 0.5
            
            drift_results.append(DriftMetrics(
                feature_name=col,
                mean_shift=float(mean_shift),
                std_shift=float(std_shift),
                distribution_distance=float(dist),
                is_drifted=is_drifted,
            ))
        
        self._last_drift_check = datetime.utcnow()
        
        drifted_features = [d.feature_name for d in drift_results if d.is_drifted]
        if drifted_features:
            logger.warning(
                "Data drift detected",
                drifted_features=drifted_features,
            )
        
        return drift_results
    
    def should_retrain(self) -> tuple[bool, RetrainingTrigger]:
        """
        Determine if model should be retrained.
        
        Returns:
            Tuple of (should_retrain, reason)
        """
        # Check performance degradation
        if self.baseline_performance and self.current_performance:
            if self.current_performance.is_degraded(self.baseline_performance):
                return True, RetrainingTrigger.PERFORMANCE_DEGRADATION
        
        # Check new samples threshold
        if self._new_samples_count >= self.min_samples:
            return True, RetrainingTrigger.NEW_DATA_THRESHOLD
        
        return False, RetrainingTrigger.SCHEDULED
    
    async def trigger_retraining(
        self,
        train_data: pd.DataFrame,
        val_data: Optional[pd.DataFrame] = None,
        trigger: RetrainingTrigger = RetrainingTrigger.MANUAL,
        model_type: str = "ensemble",
    ) -> Dict[str, Any]:
        """
        Trigger model retraining.
        
        Args:
            train_data: Training data
            val_data: Validation data
            trigger: Reason for retraining
            model_type: Type of model to train
            
        Returns:
            Training results
        """
        logger.info(
            "Triggering retraining",
            trigger=trigger.value,
            model_type=model_type,
            samples=len(train_data),
        )
        
        # Preprocess data
        train_processed, quality_report = self.data_preprocessor.fit_transform(train_data)
        
        val_processed = None
        if val_data is not None:
            val_processed, _ = self.data_preprocessor.transform(val_data)
        
        # Train model
        results = self.model_trainer.train_forecasting_model(
            train_processed,
            val_processed,
            model_type=model_type,
        )
        
        # Record retraining
        self.retraining_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "trigger": trigger.value,
            "model_type": model_type,
            "train_samples": len(train_data),
            "data_quality": quality_report.quality_score,
            "result": results.get("status"),
            "metrics": results.get("metrics"),
        })
        
        # Reset counters
        self._new_samples_count = 0
        
        # Update baseline if training successful
        if results.get("status") == "success" and results.get("metrics"):
            metrics_dict = results["metrics"]
            new_baseline = PerformanceMetrics(
                mae=metrics_dict.get('val_mae', 0),
                rmse=metrics_dict.get('val_rmse', 0),
                mape=metrics_dict.get('val_mape', 0),
                r2=0,  # Would need to compute
                timestamp=datetime.utcnow(),
            )
            self.baseline_performance = new_baseline
        
        return results
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        return {
            "running": self._running,
            "auto_retrain": self.auto_retrain,
            "new_samples_since_training": self._new_samples_count,
            "min_samples_threshold": self.min_samples,
            "baseline_performance": {
                "mae": self.baseline_performance.mae,
                "rmse": self.baseline_performance.rmse,
            } if self.baseline_performance else None,
            "current_performance": {
                "mae": self.current_performance.mae,
                "rmse": self.current_performance.rmse,
            } if self.current_performance else None,
            "last_performance_check": self._last_performance_check.isoformat() if self._last_performance_check else None,
            "last_drift_check": self._last_drift_check.isoformat() if self._last_drift_check else None,
            "retraining_count": len(self.retraining_history),
            "tracked_features": list(self.training_data_stats.keys()),
        }
    
    def get_retraining_history(self) -> List[Dict]:
        """Get history of retraining events."""
        return self.retraining_history


class ModelRegistry:
    """
    Simple model registry for tracking model versions.
    """
    
    def __init__(self, storage_path: str = "./models/registry"):
        """Initialize registry."""
        from pathlib import Path
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.registry: Dict[str, List[Dict]] = {
            "forecasting": [],
            "anomaly_detection": [],
        }
    
    def register_model(
        self,
        model_type: str,
        model_path: str,
        metrics: Dict[str, float],
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Register a trained model.
        
        Returns:
            Model version ID
        """
        import uuid
        
        version_id = str(uuid.uuid4())[:8]
        
        entry = {
            "version_id": version_id,
            "model_path": model_path,
            "registered_at": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "metadata": metadata or {},
            "is_active": False,
        }
        
        if model_type not in self.registry:
            self.registry[model_type] = []
        
        self.registry[model_type].append(entry)
        
        logger.info(
            "Model registered",
            model_type=model_type,
            version_id=version_id,
        )
        
        return version_id
    
    def set_active_model(self, model_type: str, version_id: str):
        """Set a model as the active production model."""
        if model_type not in self.registry:
            raise ValueError(f"Unknown model type: {model_type}")
        
        for entry in self.registry[model_type]:
            entry["is_active"] = entry["version_id"] == version_id
        
        logger.info(
            "Active model set",
            model_type=model_type,
            version_id=version_id,
        )
    
    def get_active_model(self, model_type: str) -> Optional[Dict]:
        """Get the currently active model."""
        if model_type not in self.registry:
            return None
        
        for entry in self.registry[model_type]:
            if entry.get("is_active"):
                return entry
        return None
    
    def list_models(self, model_type: str) -> List[Dict]:
        """List all registered models of a type."""
        return self.registry.get(model_type, [])
