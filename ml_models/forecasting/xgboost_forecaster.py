"""
XGBoost-based AQI Forecaster
Gradient boosted trees for short-term AQI prediction with uncertainty quantification.
"""

import numpy as np
import pandas as pd
import xgboost as xgb
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import joblib
import logging
from pathlib import Path

from .feature_engineering import FeatureEngineer

logger = logging.getLogger(__name__)


class XGBoostAQIForecaster:
    """
    XGBoost-based AQI forecaster with:
    - Quantile regression for uncertainty bounds
    - Feature importance analysis
    - SHAP-based interpretability
    """
    
    def __init__(
        self,
        model_dir: str = "./ml_models/artifacts",
        forecast_horizon: int = 24,
        quantiles: Tuple[float, ...] = (0.1, 0.5, 0.9),
    ):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.forecast_horizon = forecast_horizon
        self.quantiles = quantiles
        
        self.models: Dict[float, xgb.XGBRegressor] = {}
        self.feature_engineer = FeatureEngineer()
        self.feature_names: List[str] = []
        self.is_trained = False
        
        # Default hyperparameters (tuned for environmental time series)
        self.default_params = {
            "n_estimators": 500,
            "max_depth": 8,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 5,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
            "n_jobs": -1,
            "early_stopping_rounds": 50,
        }
    
    def train(
        self,
        train_data: pd.DataFrame,
        val_data: Optional[pd.DataFrame] = None,
        target_col: str = "aqi",
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Train XGBoost models for each quantile.
        
        Args:
            train_data: Training DataFrame with timestamp index
            val_data: Optional validation DataFrame
            target_col: Target column name
            params: Optional custom hyperparameters
        
        Returns:
            Training metrics dictionary
        """
        logger.info("Starting XGBoost training...")
        
        # Feature engineering
        X_train = self.feature_engineer.create_features(train_data, target_col)
        y_train = train_data[target_col].shift(-self.forecast_horizon)
        
        # Align and drop NaN
        valid_idx = y_train.dropna().index
        X_train = X_train.loc[valid_idx]
        y_train = y_train.loc[valid_idx]
        
        self.feature_names = X_train.columns.tolist()
        
        # Handle NaN in features
        X_train = X_train.fillna(0)
        
        # Prepare validation set
        X_val, y_val = None, None
        if val_data is not None:
            X_val = self.feature_engineer.create_features(val_data, target_col)
            y_val = val_data[target_col].shift(-self.forecast_horizon)
            valid_idx_val = y_val.dropna().index
            X_val = X_val.loc[valid_idx_val].fillna(0)
            y_val = y_val.loc[valid_idx_val]
        
        final_params = {**self.default_params, **(params or {})}
        metrics = {"quantiles": {}}
        
        # Train a model for each quantile
        for q in self.quantiles:
            logger.info(f"Training model for quantile {q}")
            
            # Set objective for quantile regression
            if q == 0.5:
                objective = "reg:squarederror"
            else:
                objective = "reg:quantileerror"
            
            model = xgb.XGBRegressor(
                **{k: v for k, v in final_params.items() if k != "early_stopping_rounds"},
                objective=objective,
                quantile_alpha=q if q != 0.5 else None,
            )
            
            eval_set = [(X_train, y_train)]
            if X_val is not None:
                eval_set.append((X_val, y_val))
            
            model.fit(
                X_train, y_train,
                eval_set=eval_set,
                verbose=False,
            )
            
            self.models[q] = model
            
            # Compute metrics
            train_pred = model.predict(X_train)
            train_mae = np.mean(np.abs(train_pred - y_train))
            train_rmse = np.sqrt(np.mean((train_pred - y_train) ** 2))
            
            metrics["quantiles"][q] = {
                "train_mae": float(train_mae),
                "train_rmse": float(train_rmse),
            }
            
            if X_val is not None:
                val_pred = model.predict(X_val)
                val_mae = np.mean(np.abs(val_pred - y_val))
                val_rmse = np.sqrt(np.mean((val_pred - y_val) ** 2))
                metrics["quantiles"][q]["val_mae"] = float(val_mae)
                metrics["quantiles"][q]["val_rmse"] = float(val_rmse)
        
        self.is_trained = True
        metrics["n_features"] = len(self.feature_names)
        metrics["n_train_samples"] = len(X_train)
        metrics["trained_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Training complete. Median model RMSE: {metrics['quantiles'][0.5]['train_rmse']:.2f}")
        
        return metrics
    
    def predict(
        self,
        data: pd.DataFrame,
        target_col: str = "aqi",
        return_features: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate predictions with uncertainty bounds.
        
        Args:
            data: Input DataFrame with timestamp index
            target_col: Target column name
            return_features: If True, include computed features
        
        Returns:
            Dictionary with predictions and metadata
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first or load a saved model.")
        
        X = self.feature_engineer.create_features(data, target_col).fillna(0)
        
        predictions = {}
        for q, model in self.models.items():
            predictions[q] = model.predict(X)
        
        # Primary prediction is median
        result = {
            "predicted_aqi": predictions[0.5].tolist(),
            "aqi_lower": predictions[self.quantiles[0]].tolist(),
            "aqi_upper": predictions[self.quantiles[-1]].tolist(),
            "timestamps": X.index.tolist(),
            "horizon_hours": self.forecast_horizon,
            "model_name": "XGBoost Quantile Regression",
            "model_version": "1.0.0",
        }
        
        if return_features:
            result["features"] = X.to_dict(orient="list")
            result["feature_names"] = self.feature_names
        
        return result
    
    def get_feature_importance(self, importance_type: str = "gain") -> Dict[str, float]:
        """
        Get feature importance scores from median model.
        
        Args:
            importance_type: 'gain', 'weight', or 'cover'
        
        Returns:
            Dictionary of feature name -> importance score
        """
        if not self.is_trained:
            raise ValueError("Model not trained.")
        
        model = self.models[0.5]
        importance = model.get_booster().get_score(importance_type=importance_type)
        
        # Normalize to sum to 1
        total = sum(importance.values()) or 1
        return {k: v / total for k, v in sorted(importance.items(), key=lambda x: -x[1])}
    
    def explain_prediction(self, data: pd.DataFrame, sample_idx: int = -1) -> Dict[str, Any]:
        """
        Generate SHAP-based explanation for a prediction.
        
        Args:
            data: Input DataFrame
            sample_idx: Index of sample to explain (-1 for last)
        
        Returns:
            Dictionary with SHAP values and interpretation
        """
        try:
            import shap
        except ImportError:
            return {"error": "SHAP not installed. Run: pip install shap"}
        
        if not self.is_trained:
            raise ValueError("Model not trained.")
        
        X = self.feature_engineer.create_features(data, "aqi").fillna(0)
        model = self.models[0.5]
        
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        
        sample = X.iloc[sample_idx:sample_idx+1] if sample_idx >= 0 else X.iloc[-1:]
        sample_shap = shap_values[sample_idx] if sample_idx >= 0 else shap_values[-1]
        
        # Get top contributing features
        feature_contributions = list(zip(self.feature_names, sample_shap))
        feature_contributions.sort(key=lambda x: abs(x[1]), reverse=True)
        
        return {
            "base_value": float(explainer.expected_value),
            "predicted_value": float(model.predict(sample)[0]),
            "top_features": [
                {"feature": f, "contribution": float(c)}
                for f, c in feature_contributions[:10]
            ],
            "interpretation": self._generate_interpretation(feature_contributions[:5]),
        }
    
    def _generate_interpretation(self, top_contributions: List[Tuple[str, float]]) -> str:
        """Generate human-readable interpretation of prediction drivers."""
        lines = ["Key factors driving this AQI prediction:"]
        
        for feature, contrib in top_contributions:
            direction = "increasing" if contrib > 0 else "decreasing"
            impact = abs(contrib)
            
            if "pm25" in feature.lower():
                lines.append(f"• PM2.5 levels are {direction} the predicted AQI by {impact:.1f} points")
            elif "roll_mean" in feature:
                window = feature.split("_")[-1]
                lines.append(f"• Recent {window} average is {direction} the forecast")
            elif "hour" in feature:
                lines.append(f"• Time of day effect is {direction} the prediction")
            elif "wind" in feature:
                lines.append(f"• Wind conditions are {direction} expected pollution levels")
            elif "lag" in feature:
                lines.append(f"• Historical pattern ({feature}) is {direction} the forecast")
            else:
                lines.append(f"• {feature} is {direction} the prediction by {impact:.1f}")
        
        return "\n".join(lines)
    
    def save(self, model_name: str = "xgboost_aqi"):
        """Save trained models and metadata."""
        if not self.is_trained:
            raise ValueError("No trained model to save.")
        
        save_path = self.model_dir / model_name
        save_path.mkdir(parents=True, exist_ok=True)
        
        for q, model in self.models.items():
            model.save_model(str(save_path / f"model_q{q}.json"))
        
        metadata = {
            "forecast_horizon": self.forecast_horizon,
            "quantiles": list(self.quantiles),
            "feature_names": self.feature_names,
            "saved_at": datetime.utcnow().isoformat(),
        }
        joblib.dump(metadata, save_path / "metadata.joblib")
        
        logger.info(f"Model saved to {save_path}")
    
    def load(self, model_name: str = "xgboost_aqi"):
        """Load trained models from disk."""
        load_path = self.model_dir / model_name
        
        if not load_path.exists():
            raise FileNotFoundError(f"Model not found at {load_path}")
        
        metadata = joblib.load(load_path / "metadata.joblib")
        self.forecast_horizon = metadata["forecast_horizon"]
        self.quantiles = tuple(metadata["quantiles"])
        self.feature_names = metadata["feature_names"]
        
        self.models = {}
        for q in self.quantiles:
            model = xgb.XGBRegressor()
            model.load_model(str(load_path / f"model_q{q}.json"))
            self.models[q] = model
        
        self.is_trained = True
        logger.info(f"Model loaded from {load_path}")
