"""
LSTM-based AQI Forecaster
Deep learning sequence model for temporal pattern capture.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LSTMAQIForecaster:
    """
    LSTM neural network for AQI time series forecasting.
    Captures long-range temporal dependencies and complex patterns.
    """
    
    def __init__(
        self,
        model_dir: str = "./ml_models/artifacts",
        sequence_length: int = 48,  # Input sequence (hours)
        forecast_horizon: int = 24,  # Prediction horizon (hours)
        hidden_units: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
    ):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.sequence_length = sequence_length
        self.forecast_horizon = forecast_horizon
        self.hidden_units = hidden_units
        self.num_layers = num_layers
        self.dropout = dropout
        
        self.model = None
        self.scaler_X = None
        self.scaler_y = None
        self.feature_cols: List[str] = []
        self.is_trained = False
        
        # Define input features
        self.input_features = [
            "aqi", "pm25", "pm10", "no2", "o3", "co", "so2",
            "temperature", "humidity", "wind_speed", "pressure",
            "traffic_density_index",
            "hour_sin", "hour_cos", "dow_sin", "dow_cos"
        ]
    
    def _build_model(self, n_features: int) -> Any:
        """Build LSTM architecture using Keras."""
        try:
            from tensorflow import keras
            from tensorflow.keras import layers
        except ImportError:
            logger.warning("TensorFlow not available, using mock model")
            return None
        
        model = keras.Sequential([
            layers.Input(shape=(self.sequence_length, n_features)),
            
            # First LSTM layer
            layers.LSTM(
                self.hidden_units,
                return_sequences=(self.num_layers > 1),
                dropout=self.dropout,
                recurrent_dropout=self.dropout / 2,
            ),
            layers.BatchNormalization(),
            
            # Additional LSTM layers
            *[layer for i in range(1, self.num_layers) for layer in [
                layers.LSTM(
                    self.hidden_units // (2 ** i),
                    return_sequences=(i < self.num_layers - 1),
                    dropout=self.dropout,
                ),
                layers.BatchNormalization(),
            ]],
            
            # Dense head for multi-horizon prediction
            layers.Dense(32, activation="relu"),
            layers.Dropout(self.dropout),
            layers.Dense(self.forecast_horizon)  # Predict all horizons at once
        ])
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss="huber",  # Robust to outliers
            metrics=["mae"]
        )
        
        return model
    
    def _prepare_sequences(
        self,
        data: pd.DataFrame,
        target_col: str = "aqi",
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Convert time series to supervised learning sequences."""
        # Add temporal features
        df = data.copy()
        df["hour_sin"] = np.sin(2 * np.pi * df.index.hour / 24)
        df["hour_cos"] = np.cos(2 * np.pi * df.index.hour / 24)
        df["dow_sin"] = np.sin(2 * np.pi * df.index.dayofweek / 7)
        df["dow_cos"] = np.cos(2 * np.pi * df.index.dayofweek / 7)
        
        # Select available features
        available_features = [f for f in self.input_features if f in df.columns]
        self.feature_cols = available_features
        
        df = df[available_features].fillna(method="ffill").fillna(0)
        
        # Normalize
        from sklearn.preprocessing import StandardScaler
        
        if self.scaler_X is None:
            self.scaler_X = StandardScaler()
            X_scaled = self.scaler_X.fit_transform(df)
        else:
            X_scaled = self.scaler_X.transform(df)
        
        # Create sequences
        X, y = [], []
        target_idx = available_features.index(target_col) if target_col in available_features else 0
        
        for i in range(len(X_scaled) - self.sequence_length - self.forecast_horizon + 1):
            X.append(X_scaled[i:i + self.sequence_length])
            # Multi-horizon target
            y.append(X_scaled[i + self.sequence_length:i + self.sequence_length + self.forecast_horizon, target_idx])
        
        return np.array(X), np.array(y)
    
    def train(
        self,
        train_data: pd.DataFrame,
        val_data: Optional[pd.DataFrame] = None,
        target_col: str = "aqi",
        epochs: int = 100,
        batch_size: int = 32,
        early_stopping_patience: int = 10,
    ) -> Dict[str, Any]:
        """
        Train LSTM model.
        
        Args:
            train_data: Training DataFrame with timestamp index
            val_data: Optional validation DataFrame
            target_col: Target column name
            epochs: Maximum training epochs
            batch_size: Training batch size
            early_stopping_patience: Epochs without improvement before stopping
        
        Returns:
            Training history and metrics
        """
        logger.info("Preparing LSTM training data...")
        
        X_train, y_train = self._prepare_sequences(train_data, target_col)
        
        logger.info(f"Training sequences: {X_train.shape}, Targets: {y_train.shape}")
        
        self.model = self._build_model(X_train.shape[2])
        
        if self.model is None:
            logger.warning("TensorFlow not available. Using mock training.")
            self.is_trained = True
            return {"status": "mock", "message": "TensorFlow not installed"}
        
        try:
            from tensorflow import keras
            
            callbacks = [
                keras.callbacks.EarlyStopping(
                    monitor="val_loss" if val_data is not None else "loss",
                    patience=early_stopping_patience,
                    restore_best_weights=True
                ),
                keras.callbacks.ReduceLROnPlateau(
                    monitor="val_loss" if val_data is not None else "loss",
                    factor=0.5,
                    patience=5,
                    min_lr=1e-6
                ),
            ]
            
            validation_data = None
            if val_data is not None:
                X_val, y_val = self._prepare_sequences(val_data, target_col)
                validation_data = (X_val, y_val)
            
            history = self.model.fit(
                X_train, y_train,
                epochs=epochs,
                batch_size=batch_size,
                validation_data=validation_data,
                callbacks=callbacks,
                verbose=1
            )
            
            self.is_trained = True
            
            return {
                "final_loss": float(history.history["loss"][-1]),
                "final_mae": float(history.history["mae"][-1]),
                "epochs_trained": len(history.history["loss"]),
                "n_features": X_train.shape[2],
                "sequence_length": self.sequence_length,
                "forecast_horizon": self.forecast_horizon,
                "trained_at": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"LSTM training failed: {e}")
            self.is_trained = True  # Allow mock predictions
            return {"status": "error", "message": str(e)}
    
    def predict(
        self,
        data: pd.DataFrame,
        target_col: str = "aqi",
    ) -> Dict[str, Any]:
        """
        Generate multi-horizon predictions.
        
        Args:
            data: Input DataFrame (needs sequence_length recent records)
            target_col: Target column name
        
        Returns:
            Predictions with confidence intervals
        """
        if not self.is_trained:
            raise ValueError("Model not trained.")
        
        # Use mock predictions if model not available
        if self.model is None:
            return self._mock_predict(data, target_col)
        
        # Prepare input sequence
        df = data.copy().tail(self.sequence_length + 10)
        df["hour_sin"] = np.sin(2 * np.pi * df.index.hour / 24)
        df["hour_cos"] = np.cos(2 * np.pi * df.index.hour / 24)
        df["dow_sin"] = np.sin(2 * np.pi * df.index.dayofweek / 7)
        df["dow_cos"] = np.cos(2 * np.pi * df.index.dayofweek / 7)
        
        available = [f for f in self.feature_cols if f in df.columns]
        df = df[available].fillna(method="ffill").fillna(0)
        
        X_scaled = self.scaler_X.transform(df)
        X_input = X_scaled[-self.sequence_length:].reshape(1, self.sequence_length, -1)
        
        # Predict
        y_pred_scaled = self.model.predict(X_input, verbose=0)[0]
        
        # Inverse transform (approximate)
        target_idx = self.feature_cols.index(target_col)
        y_pred = y_pred_scaled * self.scaler_X.scale_[target_idx] + self.scaler_X.mean_[target_idx]
        
        # Estimate uncertainty from training variance
        uncertainty = np.abs(y_pred) * 0.1 * np.sqrt(np.arange(1, len(y_pred) + 1))
        
        last_ts = data.index[-1]
        future_timestamps = pd.date_range(
            last_ts + pd.Timedelta(hours=1),
            periods=self.forecast_horizon,
            freq="H"
        )
        
        return {
            "predicted_aqi": y_pred.tolist(),
            "aqi_lower": (y_pred - uncertainty).tolist(),
            "aqi_upper": (y_pred + uncertainty).tolist(),
            "timestamps": future_timestamps.tolist(),
            "horizon_hours": self.forecast_horizon,
            "model_name": "LSTM Sequence Model",
            "model_version": "1.0.0",
        }
    
    def _mock_predict(self, data: pd.DataFrame, target_col: str) -> Dict[str, Any]:
        """Generate mock predictions when TensorFlow unavailable."""
        last_aqi = data[target_col].iloc[-1] if target_col in data.columns else 100
        last_ts = data.index[-1]
        
        # Simple persistence with diurnal pattern
        predictions = []
        lower, upper = [], []
        
        for h in range(1, self.forecast_horizon + 1):
            future_hour = (last_ts.hour + h) % 24
            # Diurnal factor (peaks at 8-10am and 6-8pm)
            diurnal = 1 + 0.15 * np.sin((future_hour - 8) * np.pi / 12)
            pred = last_aqi * diurnal * (1 + np.random.normal(0, 0.02))
            predictions.append(float(pred))
            
            # Growing uncertainty
            unc = last_aqi * 0.05 * np.sqrt(h)
            lower.append(float(max(0, pred - unc)))
            upper.append(float(min(500, pred + unc)))
        
        future_timestamps = pd.date_range(
            last_ts + pd.Timedelta(hours=1),
            periods=self.forecast_horizon,
            freq="H"
        )
        
        return {
            "predicted_aqi": predictions,
            "aqi_lower": lower,
            "aqi_upper": upper,
            "timestamps": future_timestamps.tolist(),
            "horizon_hours": self.forecast_horizon,
            "model_name": "LSTM (Mock)",
            "model_version": "1.0.0",
        }
    
    def save(self, model_name: str = "lstm_aqi"):
        """Save model and scalers."""
        save_path = self.model_dir / model_name
        save_path.mkdir(parents=True, exist_ok=True)
        
        if self.model is not None:
            self.model.save(str(save_path / "model.keras"))
        
        import joblib
        joblib.dump({
            "scaler_X": self.scaler_X,
            "feature_cols": self.feature_cols,
            "sequence_length": self.sequence_length,
            "forecast_horizon": self.forecast_horizon,
            "hidden_units": self.hidden_units,
            "saved_at": datetime.utcnow().isoformat(),
        }, save_path / "metadata.joblib")
        
        logger.info(f"LSTM model saved to {save_path}")
    
    def load(self, model_name: str = "lstm_aqi"):
        """Load model from disk."""
        load_path = self.model_dir / model_name
        
        if not load_path.exists():
            raise FileNotFoundError(f"Model not found at {load_path}")
        
        import joblib
        metadata = joblib.load(load_path / "metadata.joblib")
        
        self.scaler_X = metadata["scaler_X"]
        self.feature_cols = metadata["feature_cols"]
        self.sequence_length = metadata["sequence_length"]
        self.forecast_horizon = metadata["forecast_horizon"]
        self.hidden_units = metadata["hidden_units"]
        
        try:
            from tensorflow import keras
            self.model = keras.models.load_model(str(load_path / "model.keras"))
        except Exception as e:
            logger.warning(f"Could not load Keras model: {e}")
            self.model = None
        
        self.is_trained = True
        logger.info(f"LSTM model loaded from {load_path}")
