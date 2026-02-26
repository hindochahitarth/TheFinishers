"""
Ensemble Forecaster — Combines XGBoost and LSTM predictions
Weighted averaging with dynamic confidence-based weighting.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

from .xgboost_forecaster import XGBoostAQIForecaster
from .lstm_forecaster import LSTMAQIForecaster

logger = logging.getLogger(__name__)


class EnsembleForecaster:
    """
    Hybrid ensemble combining:
    - XGBoost (tabular features, interpretable)
    - LSTM (sequential patterns, long-range dependencies)
    
    Uses dynamic weighting based on recent validation performance.
    """
    
    def __init__(
        self,
        model_dir: str = "./ml_models/artifacts",
        forecast_horizon: int = 24,
        xgb_weight: float = 0.6,
        lstm_weight: float = 0.4,
    ):
        self.model_dir = model_dir
        self.forecast_horizon = forecast_horizon
        
        self.xgb_forecaster = XGBoostAQIForecaster(
            model_dir=model_dir,
            forecast_horizon=forecast_horizon
        )
        self.lstm_forecaster = LSTMAQIForecaster(
            model_dir=model_dir,
            forecast_horizon=forecast_horizon
        )
        
        # Default weights (can be updated dynamically)
        self.xgb_weight = xgb_weight
        self.lstm_weight = lstm_weight
        
        self.is_trained = False
        self.training_metrics: Dict[str, Any] = {}
    
    def train(
        self,
        train_data: pd.DataFrame,
        val_data: Optional[pd.DataFrame] = None,
        target_col: str = "aqi",
        update_weights: bool = True,
    ) -> Dict[str, Any]:
        """
        Train both component models and optionally update ensemble weights.
        
        Args:
            train_data: Training DataFrame
            val_data: Validation DataFrame for weight calibration
            target_col: Target column
            update_weights: Whether to recalibrate ensemble weights
        
        Returns:
            Combined training metrics
        """
        logger.info("Training ensemble forecaster...")
        
        # Train XGBoost
        logger.info("Training XGBoost component...")
        xgb_metrics = self.xgb_forecaster.train(train_data, val_data, target_col)
        
        # Train LSTM
        logger.info("Training LSTM component...")
        lstm_metrics = self.lstm_forecaster.train(train_data, val_data, target_col)
        
        # Update weights based on validation performance
        if update_weights and val_data is not None:
            self._calibrate_weights(val_data, target_col)
        
        self.is_trained = True
        
        self.training_metrics = {
            "xgboost": xgb_metrics,
            "lstm": lstm_metrics,
            "ensemble_weights": {"xgboost": self.xgb_weight, "lstm": self.lstm_weight},
            "trained_at": datetime.utcnow().isoformat(),
        }
        
        return self.training_metrics
    
    def _calibrate_weights(self, val_data: pd.DataFrame, target_col: str):
        """Calibrate ensemble weights using validation set."""
        try:
            # Get predictions from both models
            xgb_pred = self.xgb_forecaster.predict(val_data, target_col)
            lstm_pred = self.lstm_forecaster.predict(val_data, target_col)
            
            # Get actual values (shifted by horizon)
            y_true = val_data[target_col].shift(-self.forecast_horizon).dropna()
            
            if len(y_true) < 10:
                logger.warning("Insufficient validation data for weight calibration")
                return
            
            # Calculate errors
            n_pred = min(len(xgb_pred["predicted_aqi"]), len(y_true))
            
            xgb_error = np.mean(np.abs(
                np.array(xgb_pred["predicted_aqi"][:n_pred]) - y_true.values[:n_pred]
            ))
            lstm_error = np.mean(np.abs(
                np.array(lstm_pred["predicted_aqi"][:n_pred]) - y_true.values[:n_pred]
            ))
            
            # Inverse error weighting (lower error = higher weight)
            total_inv_error = (1 / (xgb_error + 1e-6)) + (1 / (lstm_error + 1e-6))
            self.xgb_weight = (1 / (xgb_error + 1e-6)) / total_inv_error
            self.lstm_weight = (1 / (lstm_error + 1e-6)) / total_inv_error
            
            logger.info(f"Calibrated weights - XGBoost: {self.xgb_weight:.3f}, LSTM: {self.lstm_weight:.3f}")
            
        except Exception as e:
            logger.warning(f"Weight calibration failed: {e}. Using default weights.")
    
    def predict(
        self,
        data: pd.DataFrame,
        target_col: str = "aqi",
        return_component_predictions: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate ensemble predictions.
        
        Args:
            data: Input DataFrame
            target_col: Target column
            return_component_predictions: Include individual model predictions
        
        Returns:
            Ensemble predictions with uncertainty bounds
        """
        if not self.is_trained:
            raise ValueError("Ensemble not trained.")
        
        # Get component predictions
        xgb_pred = self.xgb_forecaster.predict(data, target_col)
        lstm_pred = self.lstm_forecaster.predict(data, target_col)
        
        # Weighted average
        n_points = min(len(xgb_pred["predicted_aqi"]), len(lstm_pred["predicted_aqi"]))
        
        ensemble_pred = [
            self.xgb_weight * xgb_pred["predicted_aqi"][i] + 
            self.lstm_weight * lstm_pred["predicted_aqi"][i]
            for i in range(n_points)
        ]
        
        # Combined uncertainty bounds (wider of the two + disagreement)
        lower_bounds = []
        upper_bounds = []
        for i in range(n_points):
            xgb_l, xgb_u = xgb_pred["aqi_lower"][i], xgb_pred["aqi_upper"][i]
            lstm_l, lstm_u = lstm_pred["aqi_lower"][i], lstm_pred["aqi_upper"][i]
            
            # Model disagreement adds uncertainty
            disagreement = abs(xgb_pred["predicted_aqi"][i] - lstm_pred["predicted_aqi"][i])
            
            lower_bounds.append(max(0, min(xgb_l, lstm_l) - disagreement * 0.2))
            upper_bounds.append(min(500, max(xgb_u, lstm_u) + disagreement * 0.2))
        
        # Calculate confidence (inverse of relative uncertainty)
        confidences = []
        for i in range(n_points):
            uncertainty_range = upper_bounds[i] - lower_bounds[i]
            pred_value = max(ensemble_pred[i], 1)  # Avoid division by zero
            confidence = max(0, 1 - (uncertainty_range / (pred_value * 2)))
            confidences.append(round(confidence, 3))
        
        # Get AQI categories
        categories = [self._aqi_to_category(aqi) for aqi in ensemble_pred]
        
        result = {
            "location_id": 1,
            "generated_at": datetime.utcnow().isoformat(),
            "horizon_hours": self.forecast_horizon,
            "model_name": "GreenPulse Ensemble (XGBoost + LSTM)",
            "model_version": "1.0.0",
            "forecast": [
                {
                    "timestamp": str(xgb_pred["timestamps"][i]) if i < len(xgb_pred["timestamps"]) else None,
                    "aqi_predicted": round(ensemble_pred[i], 1),
                    "aqi_lower": round(lower_bounds[i], 1),
                    "aqi_upper": round(upper_bounds[i], 1),
                    "aqi_category": categories[i],
                    "confidence": confidences[i],
                }
                for i in range(n_points)
            ],
            "ensemble_weights": {
                "xgboost": round(self.xgb_weight, 3),
                "lstm": round(self.lstm_weight, 3),
            },
            "feature_importance": self.xgb_forecaster.get_feature_importance() if self.xgb_forecaster.is_trained else {},
        }
        
        if return_component_predictions:
            result["component_predictions"] = {
                "xgboost": xgb_pred,
                "lstm": lstm_pred,
            }
        
        return result
    
    def _aqi_to_category(self, aqi: float) -> str:
        """Convert AQI value to category."""
        if aqi <= 50:
            return "Good"
        elif aqi <= 100:
            return "Satisfactory"
        elif aqi <= 200:
            return "Moderate"
        elif aqi <= 300:
            return "Poor"
        elif aqi <= 400:
            return "Very Poor"
        else:
            return "Severe"
    
    def explain_forecast(
        self, 
        data: pd.DataFrame,
        forecast_hour: int = 1
    ) -> Dict[str, Any]:
        """
        Explain what's driving the forecast.
        
        Args:
            data: Input data
            forecast_hour: Which horizon point to explain (1-based)
        
        Returns:
            Explanation with feature contributions
        """
        if not self.is_trained:
            raise ValueError("Ensemble not trained.")
        
        # Get XGBoost explanation (more interpretable)
        xgb_explanation = self.xgb_forecaster.explain_prediction(data)
        
        # Get ensemble prediction
        ensemble_pred = self.predict(data)
        
        pred_point = ensemble_pred["forecast"][forecast_hour - 1] if forecast_hour <= len(ensemble_pred["forecast"]) else ensemble_pred["forecast"][0]
        
        return {
            "forecast_hour": forecast_hour,
            "predicted_aqi": pred_point["aqi_predicted"],
            "predicted_category": pred_point["aqi_category"],
            "confidence": pred_point["confidence"],
            "key_drivers": xgb_explanation.get("top_features", []),
            "interpretation": xgb_explanation.get("interpretation", ""),
            "model_weights": ensemble_pred["ensemble_weights"],
        }
    
    def save(self, model_name: str = "ensemble"):
        """Save both component models."""
        self.xgb_forecaster.save(f"{model_name}_xgboost")
        self.lstm_forecaster.save(f"{model_name}_lstm")
        
        # Save ensemble metadata
        import joblib
        from pathlib import Path
        
        save_path = Path(self.model_dir) / model_name
        save_path.mkdir(parents=True, exist_ok=True)
        
        joblib.dump({
            "xgb_weight": self.xgb_weight,
            "lstm_weight": self.lstm_weight,
            "forecast_horizon": self.forecast_horizon,
            "training_metrics": self.training_metrics,
            "saved_at": datetime.utcnow().isoformat(),
        }, save_path / "ensemble_meta.joblib")
        
        logger.info(f"Ensemble saved to {save_path}")
    
    def load(self, model_name: str = "ensemble"):
        """Load both component models."""
        self.xgb_forecaster.load(f"{model_name}_xgboost")
        self.lstm_forecaster.load(f"{model_name}_lstm")
        
        import joblib
        from pathlib import Path
        
        load_path = Path(self.model_dir) / model_name
        meta = joblib.load(load_path / "ensemble_meta.joblib")
        
        self.xgb_weight = meta["xgb_weight"]
        self.lstm_weight = meta["lstm_weight"]
        self.forecast_horizon = meta["forecast_horizon"]
        self.training_metrics = meta.get("training_metrics", {})
        self.is_trained = True
        
        logger.info(f"Ensemble loaded from {load_path}")


def create_mock_forecast(
    location_id: int,
    hours: int = 24,
    base_aqi: float = 100,
) -> Dict[str, Any]:
    """
    Create realistic mock forecast for demo/testing.
    Used when models aren't trained yet.
    """
    now = datetime.utcnow()
    forecasts = []
    
    for h in range(1, hours + 1):
        future_time = now + pd.Timedelta(hours=h)
        hour = (future_time.hour + 5) % 24  # IST offset
        
        # Diurnal pattern
        diurnal = 1 + 0.25 * np.sin((hour - 8) * np.pi / 12)
        
        # Random walk with mean reversion
        noise = np.random.normal(0, base_aqi * 0.05)
        pred = max(10, base_aqi * diurnal + noise)
        
        # Growing uncertainty
        uncertainty = base_aqi * 0.08 * np.sqrt(h)
        
        category = (
            "Good" if pred <= 50 else
            "Satisfactory" if pred <= 100 else
            "Moderate" if pred <= 200 else
            "Poor" if pred <= 300 else
            "Very Poor" if pred <= 400 else
            "Severe"
        )
        
        forecasts.append({
            "timestamp": future_time.isoformat(),
            "aqi_predicted": round(pred, 1),
            "aqi_lower": round(max(0, pred - uncertainty), 1),
            "aqi_upper": round(min(500, pred + uncertainty), 1),
            "aqi_category": category,
            "pm25_predicted": round(pred * 0.4 + np.random.normal(0, 5), 1),
            "no2_predicted": round(pred * 0.3 + np.random.normal(0, 4), 1),
            "confidence": round(max(0.5, 0.95 - h * 0.015), 3),
        })
    
    return {
        "location_id": location_id,
        "generated_at": now.isoformat(),
        "horizon_hours": hours,
        "model_name": "GreenPulse Ensemble (XGBoost + LSTM)",
        "model_version": "1.0.0",
        "forecast": forecasts,
        "feature_importance": {
            "pm25_24h_avg": 0.28,
            "pm25_lag_1h": 0.15,
            "hour_sin": 0.12,
            "wind_speed": 0.10,
            "temperature": 0.08,
            "humidity": 0.07,
            "traffic_density_index": 0.06,
            "aqi_roll_mean_6h": 0.05,
            "pressure": 0.04,
            "no2_lag_1h": 0.03,
            "is_rush_hour": 0.02,
        },
    }
