"""
Model Trainer

Handles training of forecasting and anomaly detection models.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import pandas as pd
import numpy as np
import structlog
import joblib

logger = structlog.get_logger(__name__)


class ModelTrainer:
    """
    Trains and manages ML models for GreenPulse AI.
    
    Supports:
    - XGBoost forecasting models
    - LSTM sequence models
    - Ensemble combinations
    - Anomaly detection models
    """
    
    def __init__(
        self,
        model_dir: str = "./models",
        experiment_name: str = "greenpulse",
    ):
        """
        Initialize model trainer.
        
        Args:
            model_dir: Directory to save models
            experiment_name: Name for experiment tracking
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.experiment_name = experiment_name
        
        self.training_history: List[Dict] = []
    
    def train_forecasting_model(
        self,
        train_data: pd.DataFrame,
        val_data: Optional[pd.DataFrame] = None,
        model_type: str = "ensemble",
        target_column: str = "aqi",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Train a forecasting model.
        
        Args:
            train_data: Training DataFrame
            val_data: Validation DataFrame (optional)
            model_type: Type of model ('xgboost', 'lstm', 'ensemble')
            target_column: Target variable to predict
            **kwargs: Additional model parameters
            
        Returns:
            Training results dictionary
        """
        logger.info(
            "Starting forecasting model training",
            model_type=model_type,
            train_samples=len(train_data),
            val_samples=len(val_data) if val_data is not None else 0,
        )
        
        start_time = datetime.utcnow()
        
        try:
            if model_type == "xgboost":
                results = self._train_xgboost(train_data, val_data, target_column, **kwargs)
            elif model_type == "lstm":
                results = self._train_lstm(train_data, val_data, target_column, **kwargs)
            elif model_type == "ensemble":
                results = self._train_ensemble(train_data, val_data, target_column, **kwargs)
            else:
                raise ValueError(f"Unknown model type: {model_type}")
            
            # Record training
            training_record = {
                "timestamp": start_time.isoformat(),
                "model_type": model_type,
                "train_samples": len(train_data),
                "val_samples": len(val_data) if val_data is not None else 0,
                "metrics": results.get("metrics", {}),
                "model_path": results.get("model_path"),
                "duration_seconds": (datetime.utcnow() - start_time).total_seconds(),
            }
            self.training_history.append(training_record)
            
            logger.info(
                "Forecasting model training completed",
                model_type=model_type,
                metrics=results.get("metrics"),
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise
    
    def _train_xgboost(
        self,
        train_data: pd.DataFrame,
        val_data: Optional[pd.DataFrame],
        target_column: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Train XGBoost model."""
        try:
            from ml_models.forecasting.xgboost_forecaster import XGBoostAQIForecaster
            from ml_models.forecasting.feature_engineering import FeatureEngineer
        except ImportError:
            logger.warning("XGBoost forecaster not available")
            return {"status": "not_available", "metrics": {}}
        
        # Feature engineering
        fe = FeatureEngineer()
        X_train, y_train = fe.transform(train_data, target_column=target_column)
        
        X_val, y_val = None, None
        if val_data is not None:
            X_val, y_val = fe.transform(val_data, target_column=target_column)
        
        # Train model
        model = XGBoostAQIForecaster(
            n_estimators=kwargs.get('n_estimators', 200),
            max_depth=kwargs.get('max_depth', 8),
            learning_rate=kwargs.get('learning_rate', 0.05),
        )
        
        model.fit(X_train, y_train, X_val, y_val)
        
        # Evaluate
        metrics = {}
        if y_val is not None:
            y_pred = model.predict(X_val)
            metrics['val_mae'] = np.mean(np.abs(y_val - y_pred))
            metrics['val_rmse'] = np.sqrt(np.mean((y_val - y_pred) ** 2))
            metrics['val_mape'] = np.mean(np.abs((y_val - y_pred) / (y_val + 1))) * 100
        
        # Save model
        model_path = self.model_dir / f"xgboost_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.joblib"
        model.save(str(model_path))
        
        return {
            "status": "success",
            "model_type": "xgboost",
            "model_path": str(model_path),
            "metrics": metrics,
            "feature_importance": model.get_feature_importance(),
        }
    
    def _train_lstm(
        self,
        train_data: pd.DataFrame,
        val_data: Optional[pd.DataFrame],
        target_column: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Train LSTM model."""
        try:
            from ml_models.forecasting.lstm_forecaster import LSTMAQIForecaster
        except ImportError:
            logger.warning("LSTM forecaster not available")
            return {"status": "not_available", "metrics": {}}
        
        # Prepare sequence data
        sequence_length = kwargs.get('sequence_length', 48)
        
        feature_cols = ['pm25', 'pm10', 'no2', 'o3', 'temperature', 'humidity', 'wind_speed']
        feature_cols = [c for c in feature_cols if c in train_data.columns]
        
        X_train, y_train = self._create_sequences(
            train_data, feature_cols, target_column, sequence_length
        )
        
        X_val, y_val = None, None
        if val_data is not None:
            X_val, y_val = self._create_sequences(
                val_data, feature_cols, target_column, sequence_length
            )
        
        # Train model
        model = LSTMAQIForecaster(
            sequence_length=sequence_length,
            n_features=len(feature_cols),
            hidden_units=kwargs.get('hidden_units', 64),
            n_layers=kwargs.get('n_layers', 2),
        )
        
        model.fit(
            X_train, y_train,
            X_val, y_val,
            epochs=kwargs.get('epochs', 50),
            batch_size=kwargs.get('batch_size', 32),
        )
        
        # Evaluate
        metrics = {}
        if y_val is not None:
            y_pred = model.predict(X_val)
            metrics['val_mae'] = float(np.mean(np.abs(y_val - y_pred)))
            metrics['val_rmse'] = float(np.sqrt(np.mean((y_val - y_pred) ** 2)))
        
        # Save model
        model_path = self.model_dir / f"lstm_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        model.save(str(model_path))
        
        return {
            "status": "success",
            "model_type": "lstm",
            "model_path": str(model_path),
            "metrics": metrics,
        }
    
    def _train_ensemble(
        self,
        train_data: pd.DataFrame,
        val_data: Optional[pd.DataFrame],
        target_column: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Train ensemble model (XGBoost + LSTM)."""
        try:
            from ml_models.forecasting.ensemble_forecaster import EnsembleForecaster
        except ImportError:
            logger.warning("Ensemble forecaster not available")
            return {"status": "not_available", "metrics": {}}
        
        # Train ensemble
        ensemble = EnsembleForecaster(
            xgboost_weight=kwargs.get('xgboost_weight', 0.6),
            lstm_weight=kwargs.get('lstm_weight', 0.4),
        )
        
        ensemble.fit(train_data, val_data)
        
        # Evaluate
        metrics = {}
        if val_data is not None:
            predictions = ensemble.predict(val_data, horizon_hours=1)
            if predictions:
                y_pred = [p['aqi'] for p in predictions]
                y_true = val_data[target_column].tail(len(y_pred)).values
                metrics['val_mae'] = float(np.mean(np.abs(y_true - y_pred)))
                metrics['val_rmse'] = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
        
        # Save model
        model_path = self.model_dir / f"ensemble_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        ensemble.save(str(model_path))
        
        return {
            "status": "success",
            "model_type": "ensemble",
            "model_path": str(model_path),
            "metrics": metrics,
            "weights": {
                "xgboost": ensemble.xgboost_weight,
                "lstm": ensemble.lstm_weight,
            }
        }
    
    def train_anomaly_model(
        self,
        train_data: pd.DataFrame,
        model_type: str = "isolation_forest",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Train anomaly detection model.
        
        Args:
            train_data: Training DataFrame (assumed to be "normal" data)
            model_type: Type of model ('isolation_forest', 'statistical')
            **kwargs: Additional parameters
            
        Returns:
            Training results
        """
        logger.info(
            "Training anomaly detection model",
            model_type=model_type,
            samples=len(train_data),
        )
        
        try:
            if model_type == "isolation_forest":
                from ml_models.anomaly_detection.isolation_forest import IsolationForestDetector
                
                feature_cols = kwargs.get('feature_cols', ['pm25', 'pm10', 'no2', 'o3', 'aqi'])
                feature_cols = [c for c in feature_cols if c in train_data.columns]
                
                X = train_data[feature_cols].fillna(0).values
                
                model = IsolationForestDetector(
                    contamination=kwargs.get('contamination', 0.05),
                    n_estimators=kwargs.get('n_estimators', 100),
                )
                model.fit(X)
                
                # Save model
                model_path = self.model_dir / f"isolation_forest_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.joblib"
                joblib.dump(model, str(model_path))
                
                return {
                    "status": "success",
                    "model_type": "isolation_forest",
                    "model_path": str(model_path),
                    "feature_columns": feature_cols,
                }
                
            elif model_type == "statistical":
                from ml_models.anomaly_detection.detector import AnomalyDetector
                
                model = AnomalyDetector()
                
                # Fit on each pollutant
                for col in ['pm25', 'pm10', 'no2', 'o3', 'aqi']:
                    if col in train_data.columns:
                        model.fit(train_data[col].dropna().values)
                
                model_path = self.model_dir / f"statistical_detector_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.joblib"
                joblib.dump(model, str(model_path))
                
                return {
                    "status": "success",
                    "model_type": "statistical",
                    "model_path": str(model_path),
                }
            
            else:
                raise ValueError(f"Unknown anomaly model type: {model_type}")
                
        except Exception as e:
            logger.error(f"Anomaly model training failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def _create_sequences(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str,
        sequence_length: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM training."""
        features = df[feature_cols].fillna(0).values
        target = df[target_col].fillna(0).values
        
        X, y = [], []
        for i in range(len(features) - sequence_length):
            X.append(features[i:i + sequence_length])
            y.append(target[i + sequence_length])
        
        return np.array(X), np.array(y)
    
    def get_training_history(self) -> List[Dict]:
        """Get history of training runs."""
        return self.training_history
    
    def get_latest_model(self, model_type: str) -> Optional[str]:
        """Get path to latest trained model of specified type."""
        models = list(self.model_dir.glob(f"{model_type}_*"))
        if models:
            return str(max(models, key=lambda p: p.stat().st_mtime))
        return None


def train_from_database(
    db_session,
    model_trainer: ModelTrainer,
    location_id: int = 1,
    days: int = 30,
    model_type: str = "ensemble",
) -> Dict[str, Any]:
    """
    Train model from database readings.
    
    Args:
        db_session: Database session
        model_trainer: ModelTrainer instance
        location_id: Location to train on
        days: Number of days of data to use
        model_type: Type of model to train
        
    Returns:
        Training results
    """
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from app.models.sensor_reading import SensorReading
    
    # This is a stub - in production, implement async query
    logger.info(
        "Training from database",
        location_id=location_id,
        days=days,
        model_type=model_type,
    )
    
    # Return placeholder
    return {
        "status": "pending",
        "message": "Database training requires async implementation",
    }
