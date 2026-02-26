"""
Isolation Forest Anomaly Detector
Tree-based unsupervised anomaly detection for multivariate data.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
import joblib
from pathlib import Path

logger = logging.getLogger(__name__)


class IsolationForestDetector:
    """
    Isolation Forest for detecting multivariate anomalies.
    Works by isolating outliers - anomalies are easier to isolate.
    """
    
    def __init__(
        self,
        model_dir: str = "./ml_models/artifacts",
        contamination: float = 0.05,
        n_estimators: int = 200,
        max_features: float = 0.8,
    ):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.max_features = max_features
        
        self.model = None
        self.scaler = None
        self.feature_cols: List[str] = []
        self.is_fitted = False
        
        # Features to use for anomaly detection
        self.default_features = [
            "aqi", "pm25", "pm10", "no2", "o3", "co", "so2",
            "temperature", "humidity", "wind_speed", "pressure",
            "traffic_density_index"
        ]
    
    def fit(
        self,
        data: pd.DataFrame,
        feature_cols: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Fit Isolation Forest to historical data.
        
        Args:
            data: Training DataFrame
            feature_cols: Features to use (default: all available)
        
        Returns:
            Fitting statistics
        """
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler
        
        logger.info("Fitting Isolation Forest...")
        
        # Select features
        if feature_cols:
            self.feature_cols = [c for c in feature_cols if c in data.columns]
        else:
            self.feature_cols = [c for c in self.default_features if c in data.columns]
        
        if len(self.feature_cols) < 3:
            raise ValueError(f"Need at least 3 features, found {len(self.feature_cols)}")
        
        # Prepare data
        X = data[self.feature_cols].copy()
        X = X.fillna(X.median())
        
        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Fit Isolation Forest
        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            max_features=self.max_features,
            random_state=42,
            n_jobs=-1,
        )
        self.model.fit(X_scaled)
        
        self.is_fitted = True
        
        # Calculate baseline statistics
        scores = self.model.decision_function(X_scaled)
        predictions = self.model.predict(X_scaled)
        
        return {
            "n_samples": len(X),
            "n_features": len(self.feature_cols),
            "features": self.feature_cols,
            "anomaly_rate_train": float((predictions == -1).mean()),
            "score_mean": float(scores.mean()),
            "score_std": float(scores.std()),
            "fitted_at": datetime.utcnow().isoformat(),
        }
    
    def detect(
        self,
        data: pd.DataFrame,
        return_scores: bool = True,
    ) -> Dict[str, Any]:
        """
        Detect anomalies in new data.
        
        Args:
            data: DataFrame with readings to check
            return_scores: Include anomaly scores
        
        Returns:
            Detection results
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")
        
        # Prepare data
        X = data[self.feature_cols].copy()
        X = X.fillna(X.median())
        X_scaled = self.scaler.transform(X)
        
        # Predict
        predictions = self.model.predict(X_scaled)  # -1 = anomaly, 1 = normal
        scores = self.model.decision_function(X_scaled)  # Lower = more anomalous
        
        # Convert to intuitive format
        is_anomaly = predictions == -1
        
        # Normalize scores to 0-1 (1 = most anomalous)
        min_score, max_score = scores.min(), scores.max()
        if max_score > min_score:
            anomaly_scores = 1 - (scores - min_score) / (max_score - min_score)
        else:
            anomaly_scores = np.zeros_like(scores)
        
        result = {
            "n_samples": len(data),
            "anomaly_count": int(is_anomaly.sum()),
            "anomaly_rate": float(is_anomaly.mean()),
            "is_anomaly": is_anomaly.tolist(),
        }
        
        if return_scores:
            result["anomaly_scores"] = anomaly_scores.tolist()
        
        return result
    
    def detect_single(
        self,
        reading: Dict[str, Any],
    ) -> Tuple[bool, float, str]:
        """
        Detect if a single reading is anomalous.
        
        Args:
            reading: Single sensor reading
        
        Returns:
            Tuple of (is_anomaly, anomaly_score, explanation)
        """
        if not self.is_fitted:
            return False, 0.0, "Model not fitted"
        
        # Convert to DataFrame
        df = pd.DataFrame([reading])
        
        # Check for missing features
        missing = [c for c in self.feature_cols if c not in df.columns or pd.isna(df[c].iloc[0])]
        if len(missing) > len(self.feature_cols) // 2:
            return False, 0.0, f"Insufficient data: missing {missing}"
        
        # Fill missing with median from training
        for col in self.feature_cols:
            if col not in df.columns:
                df[col] = 0  # Neutral value after scaling
        
        df = df[self.feature_cols].fillna(0)
        
        X_scaled = self.scaler.transform(df)
        
        prediction = self.model.predict(X_scaled)[0]
        score = self.model.decision_function(X_scaled)[0]
        
        is_anomaly = prediction == -1
        # Convert score to 0-1 scale
        anomaly_score = max(0, min(1, 0.5 - score * 0.5))
        
        # Generate explanation
        if is_anomaly:
            # Find which features are most anomalous
            contributing = self._find_contributing_features(df.iloc[0])
            explanation = f"Anomaly detected. Key factors: {', '.join(contributing[:3])}"
        else:
            explanation = "Reading within normal patterns"
        
        return is_anomaly, float(anomaly_score), explanation
    
    def _find_contributing_features(self, row: pd.Series) -> List[str]:
        """Identify features contributing most to anomaly."""
        if self.scaler is None:
            return []
        
        contributions = []
        for i, col in enumerate(self.feature_cols):
            value = row[col]
            mean = self.scaler.mean_[i]
            std = self.scaler.scale_[i]
            
            zscore = abs(value - mean) / std if std > 0 else 0
            contributions.append((col, zscore))
        
        # Sort by z-score
        contributions.sort(key=lambda x: -x[1])
        
        return [c[0] for c in contributions if c[1] > 1.5]
    
    def save(self, model_name: str = "isolation_forest"):
        """Save model to disk."""
        if not self.is_fitted:
            raise ValueError("No fitted model to save")
        
        save_path = self.model_dir / model_name
        save_path.mkdir(parents=True, exist_ok=True)
        
        joblib.dump({
            "model": self.model,
            "scaler": self.scaler,
            "feature_cols": self.feature_cols,
            "contamination": self.contamination,
            "saved_at": datetime.utcnow().isoformat(),
        }, save_path / "model.joblib")
        
        logger.info(f"Isolation Forest saved to {save_path}")
    
    def load(self, model_name: str = "isolation_forest"):
        """Load model from disk."""
        load_path = self.model_dir / model_name
        
        if not load_path.exists():
            raise FileNotFoundError(f"Model not found at {load_path}")
        
        data = joblib.load(load_path / "model.joblib")
        
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.feature_cols = data["feature_cols"]
        self.contamination = data["contamination"]
        self.is_fitted = True
        
        logger.info(f"Isolation Forest loaded from {load_path}")
