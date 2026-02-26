"""
Feature Engineering Module for Time Series Forecasting
Creates lag features, rolling statistics, cyclical encodings, and cross-domain features.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class FeatureEngineer:
    """
    Creates rich feature sets for AQI forecasting from multi-modal environmental data.
    """
    
    def __init__(
        self,
        pollutant_cols: List[str] = None,
        weather_cols: List[str] = None,
        lag_hours: List[int] = None,
        rolling_windows: List[int] = None,
    ):
        self.pollutant_cols = pollutant_cols or ["pm25", "pm10", "no2", "o3", "co", "so2"]
        self.weather_cols = weather_cols or [
            "temperature", "humidity", "wind_speed", "wind_direction", 
            "pressure", "visibility", "cloud_cover"
        ]
        self.lag_hours = lag_hours or [1, 2, 3, 6, 12, 24, 48]
        self.rolling_windows = rolling_windows or [3, 6, 12, 24, 48]
        self.feature_names: List[str] = []
    
    def create_features(
        self, 
        df: pd.DataFrame, 
        target_col: str = "aqi",
        include_future: bool = False
    ) -> pd.DataFrame:
        """
        Generate comprehensive feature set from raw sensor data.
        
        Args:
            df: DataFrame with timestamp index and pollutant/weather columns
            target_col: Column to predict
            include_future: If True, include features that would use future data (training only)
        
        Returns:
            DataFrame with engineered features
        """
        df = df.copy().sort_index()
        features = pd.DataFrame(index=df.index)
        
        # === 1. Temporal Features ===
        features = self._add_temporal_features(features, df)
        
        # === 2. Lag Features ===
        features = self._add_lag_features(features, df, target_col)
        
        # === 3. Rolling Statistics ===
        features = self._add_rolling_features(features, df, target_col)
        
        # === 4. Pollutant Interactions ===
        features = self._add_pollutant_interactions(features, df)
        
        # === 5. Weather-Pollution Interactions ===
        features = self._add_weather_interactions(features, df)
        
        # === 6. Trend Features ===
        features = self._add_trend_features(features, df, target_col)
        
        # === 7. Raw Weather Features ===
        for col in self.weather_cols:
            if col in df.columns:
                features[col] = df[col].values
        
        # Store feature names
        self.feature_names = features.columns.tolist()
        
        return features
    
    def _add_temporal_features(self, features: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
        """Add cyclical time encodings and temporal markers."""
        idx = df.index
        
        # Hour of day (cyclical)
        hour = idx.hour
        features["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        features["hour_cos"] = np.cos(2 * np.pi * hour / 24)
        
        # Day of week (cyclical)
        dow = idx.dayofweek
        features["dow_sin"] = np.sin(2 * np.pi * dow / 7)
        features["dow_cos"] = np.cos(2 * np.pi * dow / 7)
        
        # Month of year (cyclical) - captures seasonality
        month = idx.month
        features["month_sin"] = np.sin(2 * np.pi * month / 12)
        features["month_cos"] = np.cos(2 * np.pi * month / 12)
        
        # Rush hour indicator (India: 8-11 AM, 5-9 PM)
        features["is_rush_hour"] = ((hour >= 8) & (hour <= 11) | (hour >= 17) & (hour <= 21)).astype(int)
        
        # Weekend indicator
        features["is_weekend"] = (dow >= 5).astype(int)
        
        # Night indicator (reduced traffic, boundary layer effects)
        features["is_night"] = ((hour >= 22) | (hour <= 5)).astype(int)
        
        return features
    
    def _add_lag_features(
        self, features: pd.DataFrame, df: pd.DataFrame, target_col: str
    ) -> pd.DataFrame:
        """Add lagged values of target and key predictors."""
        for lag in self.lag_hours:
            # Target lags
            if target_col in df.columns:
                features[f"{target_col}_lag_{lag}h"] = df[target_col].shift(lag)
            
            # Key pollutant lags
            for col in ["pm25", "pm10", "no2"]:
                if col in df.columns:
                    features[f"{col}_lag_{lag}h"] = df[col].shift(lag)
        
        return features
    
    def _add_rolling_features(
        self, features: pd.DataFrame, df: pd.DataFrame, target_col: str
    ) -> pd.DataFrame:
        """Add rolling mean, std, min, max for key variables."""
        for window in self.rolling_windows:
            # Target rolling stats
            if target_col in df.columns:
                features[f"{target_col}_roll_mean_{window}h"] = (
                    df[target_col].rolling(window=window, min_periods=1).mean()
                )
                features[f"{target_col}_roll_std_{window}h"] = (
                    df[target_col].rolling(window=window, min_periods=1).std()
                )
                features[f"{target_col}_roll_max_{window}h"] = (
                    df[target_col].rolling(window=window, min_periods=1).max()
                )
                features[f"{target_col}_roll_min_{window}h"] = (
                    df[target_col].rolling(window=window, min_periods=1).min()
                )
            
            # PM2.5 rolling (primary driver)
            if "pm25" in df.columns:
                features[f"pm25_roll_mean_{window}h"] = (
                    df["pm25"].rolling(window=window, min_periods=1).mean()
                )
                features[f"pm25_roll_std_{window}h"] = (
                    df["pm25"].rolling(window=window, min_periods=1).std()
                )
        
        return features
    
    def _add_pollutant_interactions(
        self, features: pd.DataFrame, df: pd.DataFrame
    ) -> pd.DataFrame:
        """Add cross-pollutant interaction features."""
        
        # PM2.5/PM10 ratio (indicates fine particle dominance)
        if "pm25" in df.columns and "pm10" in df.columns:
            pm10_safe = df["pm10"].replace(0, np.nan)
            features["pm25_pm10_ratio"] = df["pm25"] / pm10_safe
        
        # NO2/O3 ratio (photochemical indicator)
        if "no2" in df.columns and "o3" in df.columns:
            o3_safe = df["o3"].replace(0, np.nan)
            features["no2_o3_ratio"] = df["no2"] / o3_safe
        
        # Total oxidant (NO2 + O3)
        if "no2" in df.columns and "o3" in df.columns:
            features["total_oxidant"] = df["no2"] + df["o3"]
        
        # Secondary aerosol potential (NO2 * humidity)
        if "no2" in df.columns and "humidity" in df.columns:
            features["secondary_aerosol_potential"] = df["no2"] * df["humidity"] / 100
        
        return features
    
    def _add_weather_interactions(
        self, features: pd.DataFrame, df: pd.DataFrame
    ) -> pd.DataFrame:
        """Add weather-pollution interaction features (causally relevant)."""
        
        # Wind dispersion factor (higher wind = better dispersion)
        if "wind_speed" in df.columns and "pm25" in df.columns:
            wind_safe = df["wind_speed"].replace(0, 0.1)
            features["pm25_wind_interaction"] = df["pm25"] / wind_safe
        
        # Temperature inversion indicator (low wind + temperature drop)
        if "temperature" in df.columns and "wind_speed" in df.columns:
            temp_change = df["temperature"].diff()
            features["inversion_potential"] = (
                (temp_change < -2) & (df["wind_speed"] < 2)
            ).astype(int)
        
        # Humidity-pollutant interaction (hygroscopic growth)
        if "humidity" in df.columns and "pm25" in df.columns:
            features["humidity_pm25_growth"] = (
                df["pm25"] * (1 + 0.01 * df["humidity"])
            )
        
        # Atmospheric stability index
        if all(c in df.columns for c in ["wind_speed", "cloud_cover"]):
            # Simplified Pasquill stability approximation
            features["stability_index"] = (
                (10 - df["wind_speed"]) * (100 - df["cloud_cover"]) / 1000
            )
        
        return features
    
    def _add_trend_features(
        self, features: pd.DataFrame, df: pd.DataFrame, target_col: str
    ) -> pd.DataFrame:
        """Add trend and momentum indicators."""
        if target_col not in df.columns:
            return features
        
        # Short-term change
        features[f"{target_col}_change_1h"] = df[target_col].diff(1)
        features[f"{target_col}_change_3h"] = df[target_col].diff(3)
        features[f"{target_col}_change_6h"] = df[target_col].diff(6)
        
        # Rate of change (first derivative)
        features[f"{target_col}_rate_3h"] = df[target_col].diff(3) / 3
        
        # Momentum (second derivative)
        features[f"{target_col}_momentum"] = df[target_col].diff(1).diff(1)
        
        # Percentage change from 24h ago
        lag_24 = df[target_col].shift(24)
        features[f"{target_col}_pct_change_24h"] = (
            (df[target_col] - lag_24) / lag_24.replace(0, np.nan) * 100
        )
        
        return features
    
    def get_feature_names(self) -> List[str]:
        """Return list of generated feature names."""
        return self.feature_names
    
    def get_feature_importance_groups(self) -> Dict[str, List[str]]:
        """Categorize features for interpretability."""
        groups = {
            "temporal": [],
            "lag": [],
            "rolling": [],
            "pollutant_interaction": [],
            "weather_interaction": [],
            "trend": [],
            "raw_weather": [],
        }
        
        for name in self.feature_names:
            if any(t in name for t in ["hour", "dow", "month", "rush", "weekend", "night"]):
                groups["temporal"].append(name)
            elif "lag_" in name:
                groups["lag"].append(name)
            elif "roll_" in name:
                groups["rolling"].append(name)
            elif any(t in name for t in ["ratio", "oxidant", "aerosol"]):
                groups["pollutant_interaction"].append(name)
            elif any(t in name for t in ["wind_interaction", "inversion", "growth", "stability"]):
                groups["weather_interaction"].append(name)
            elif any(t in name for t in ["change", "rate", "momentum", "pct"]):
                groups["trend"].append(name)
            else:
                groups["raw_weather"].append(name)
        
        return groups


def prepare_forecast_data(
    readings: List[Dict], 
    forecast_horizon: int = 24
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Convert sensor readings to ML-ready format.
    
    Args:
        readings: List of sensor reading dictionaries
        forecast_horizon: Hours ahead to predict
    
    Returns:
        Tuple of (features DataFrame, target Series)
    """
    df = pd.DataFrame(readings)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    
    # Fill missing values with forward fill then backward fill
    df = df.ffill().bfill()
    
    # Engineer features
    fe = FeatureEngineer()
    features = fe.create_features(df, target_col="aqi")
    
    # Create target (AQI shifted by horizon)
    target = df["aqi"].shift(-forecast_horizon)
    
    # Drop rows with NaN target
    valid_idx = target.dropna().index
    features = features.loc[valid_idx]
    target = target.loc[valid_idx]
    
    return features, target
