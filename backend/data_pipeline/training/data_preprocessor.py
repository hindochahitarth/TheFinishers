"""
Data Preprocessor for ML Pipeline

Handles data cleaning, validation, and transformation for model training.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class DataQualityReport:
    """Report on data quality metrics."""
    total_records: int
    missing_values: Dict[str, int]
    outliers_detected: Dict[str, int]
    duplicate_records: int
    valid_records: int
    quality_score: float


class DataPreprocessor:
    """
    Preprocesses environmental sensor data for ML model training.
    
    Features:
    - Missing value imputation
    - Outlier detection and handling
    - Data validation
    - Feature normalization
    - Temporal alignment
    """
    
    POLLUTANT_COLUMNS = ['pm25', 'pm10', 'no2', 'o3', 'co', 'so2', 'nh3']
    WEATHER_COLUMNS = ['temperature', 'humidity', 'wind_speed', 'wind_direction', 'pressure']
    TRAFFIC_COLUMNS = ['traffic_density_index', 'average_speed_kmh']
    
    # Reasonable bounds for outlier detection
    BOUNDS = {
        'pm25': (0, 999),
        'pm10': (0, 999),
        'no2': (0, 500),
        'o3': (0, 500),
        'co': (0, 50),
        'so2': (0, 500),
        'nh3': (0, 500),
        'temperature': (-50, 60),
        'humidity': (0, 100),
        'wind_speed': (0, 100),
        'pressure': (800, 1100),
        'aqi': (0, 500),
    }
    
    def __init__(
        self,
        imputation_method: str = 'interpolate',
        outlier_method: str = 'clip',
        normalize: bool = True,
    ):
        """
        Initialize preprocessor.
        
        Args:
            imputation_method: Method for missing values ('interpolate', 'forward_fill', 'mean')
            outlier_method: Method for outliers ('clip', 'remove', 'impute')
            normalize: Whether to normalize numerical features
        """
        self.imputation_method = imputation_method
        self.outlier_method = outlier_method
        self.normalize = normalize
        
        self.feature_stats: Dict[str, Dict] = {}
        self.is_fitted = False
    
    def fit(self, df: pd.DataFrame) -> 'DataPreprocessor':
        """
        Compute statistics needed for preprocessing.
        
        Args:
            df: Training DataFrame
            
        Returns:
            Self for chaining
        """
        numerical_cols = (
            self.POLLUTANT_COLUMNS + 
            self.WEATHER_COLUMNS + 
            self.TRAFFIC_COLUMNS + 
            ['aqi']
        )
        
        for col in numerical_cols:
            if col in df.columns:
                self.feature_stats[col] = {
                    'mean': df[col].mean(),
                    'std': df[col].std(),
                    'median': df[col].median(),
                    'q1': df[col].quantile(0.25),
                    'q3': df[col].quantile(0.75),
                    'min': df[col].min(),
                    'max': df[col].max(),
                }
        
        self.is_fitted = True
        logger.info("DataPreprocessor fitted", columns=len(self.feature_stats))
        return self
    
    def transform(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, DataQualityReport]:
        """
        Transform data for model training.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Tuple of (transformed DataFrame, quality report)
        """
        df = df.copy()
        
        # 1. Sort by timestamp
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp').reset_index(drop=True)
        
        # 2. Remove duplicates
        initial_len = len(df)
        df = df.drop_duplicates(subset=['timestamp'] if 'timestamp' in df.columns else None)
        duplicates_removed = initial_len - len(df)
        
        # 3. Handle missing values
        missing_before = df.isnull().sum().to_dict()
        df = self._impute_missing_values(df)
        
        # 4. Detect and handle outliers
        outliers_detected = self._detect_outliers(df)
        df = self._handle_outliers(df)
        
        # 5. Validate data
        df = self._validate_data(df)
        
        # 6. Normalize if needed
        if self.normalize and self.is_fitted:
            df = self._normalize_features(df)
        
        # Generate quality report
        quality_score = self._compute_quality_score(
            len(df), 
            sum(missing_before.values()), 
            sum(outliers_detected.values()),
            duplicates_removed
        )
        
        report = DataQualityReport(
            total_records=initial_len,
            missing_values={k: v for k, v in missing_before.items() if v > 0},
            outliers_detected=outliers_detected,
            duplicate_records=duplicates_removed,
            valid_records=len(df),
            quality_score=quality_score,
        )
        
        logger.info(
            "Data transformed",
            valid_records=len(df),
            quality_score=quality_score,
        )
        
        return df, report
    
    def fit_transform(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, DataQualityReport]:
        """Fit and transform in one step."""
        self.fit(df)
        return self.transform(df)
    
    def _impute_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Impute missing values based on configured method."""
        numerical_cols = [
            col for col in df.columns 
            if col in self.feature_stats or col in self.BOUNDS
        ]
        
        if self.imputation_method == 'interpolate':
            for col in numerical_cols:
                if col in df.columns:
                    df[col] = df[col].interpolate(method='linear', limit_direction='both')
                    
        elif self.imputation_method == 'forward_fill':
            for col in numerical_cols:
                if col in df.columns:
                    df[col] = df[col].ffill().bfill()
                    
        elif self.imputation_method == 'mean':
            for col in numerical_cols:
                if col in df.columns:
                    mean_val = self.feature_stats.get(col, {}).get('mean', df[col].mean())
                    df[col] = df[col].fillna(mean_val)
        
        return df
    
    def _detect_outliers(self, df: pd.DataFrame) -> Dict[str, int]:
        """Detect outliers in each column."""
        outliers = {}
        
        for col, (lower, upper) in self.BOUNDS.items():
            if col in df.columns:
                outlier_mask = (df[col] < lower) | (df[col] > upper)
                outliers[col] = outlier_mask.sum()
        
        return {k: v for k, v in outliers.items() if v > 0}
    
    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle outliers based on configured method."""
        for col, (lower, upper) in self.BOUNDS.items():
            if col not in df.columns:
                continue
                
            if self.outlier_method == 'clip':
                df[col] = df[col].clip(lower=lower, upper=upper)
                
            elif self.outlier_method == 'remove':
                outlier_mask = (df[col] < lower) | (df[col] > upper)
                df = df[~outlier_mask]
                
            elif self.outlier_method == 'impute':
                outlier_mask = (df[col] < lower) | (df[col] > upper)
                median_val = self.feature_stats.get(col, {}).get('median', df[col].median())
                df.loc[outlier_mask, col] = median_val
        
        return df.reset_index(drop=True)
    
    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate data integrity."""
        # Ensure no negative pollutant values
        for col in self.POLLUTANT_COLUMNS:
            if col in df.columns:
                df[col] = df[col].clip(lower=0)
        
        # Ensure humidity in valid range
        if 'humidity' in df.columns:
            df['humidity'] = df['humidity'].clip(0, 100)
        
        return df
    
    def _normalize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize numerical features using fitted statistics."""
        for col, stats in self.feature_stats.items():
            if col in df.columns and stats['std'] > 0:
                # Z-score normalization
                df[col] = (df[col] - stats['mean']) / stats['std']
        
        return df
    
    def _compute_quality_score(
        self,
        total_records: int,
        missing_count: int,
        outlier_count: int,
        duplicates: int,
    ) -> float:
        """Compute overall data quality score (0-1)."""
        if total_records == 0:
            return 0.0
        
        # Penalize missing values
        missing_penalty = min(0.4, (missing_count / total_records) * 2)
        
        # Penalize outliers
        outlier_penalty = min(0.3, (outlier_count / total_records) * 1.5)
        
        # Penalize duplicates
        duplicate_penalty = min(0.2, (duplicates / total_records) * 1)
        
        score = 1.0 - missing_penalty - outlier_penalty - duplicate_penalty
        return max(0.0, min(1.0, score))


def create_training_dataset(
    readings: List[Dict],
    target_column: str = 'aqi',
    sequence_length: int = 24,
    forecast_horizon: int = 1,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create training dataset with sequences for time series models.
    
    Args:
        readings: List of sensor reading dictionaries
        target_column: Column to predict
        sequence_length: Number of timesteps in input sequence
        forecast_horizon: Number of steps ahead to predict
        
    Returns:
        Tuple of (X, y) arrays
    """
    df = pd.DataFrame(readings)
    
    # Ensure sorted by time
    if 'timestamp' in df.columns:
        df = df.sort_values('timestamp')
    
    # Select feature columns
    feature_cols = [
        'pm25', 'pm10', 'no2', 'o3', 'co', 'so2',
        'temperature', 'humidity', 'wind_speed', 'wind_direction',
        'traffic_density_index',
    ]
    feature_cols = [c for c in feature_cols if c in df.columns]
    
    # Extract features and target
    features = df[feature_cols].values
    target = df[target_column].values
    
    # Create sequences
    X, y = [], []
    for i in range(len(features) - sequence_length - forecast_horizon + 1):
        X.append(features[i:i + sequence_length])
        y.append(target[i + sequence_length + forecast_horizon - 1])
    
    return np.array(X), np.array(y)
