"""
Unified Anomaly Detection System
Combines multiple detection methods with confidence aggregation.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AnomalyResult:
    """Result from anomaly detection."""
    is_anomaly: bool
    anomaly_score: float  # 0-1, higher = more anomalous
    confidence: float  # 0-1, detection confidence
    anomaly_type: str  # spike, drop, drift, pattern_break
    contributing_features: List[str]
    explanation: str


class AnomalyDetector:
    """
    Multi-method anomaly detector combining:
    1. Statistical thresholds (z-score, IQR)
    2. Isolation Forest (unsupervised ML)
    3. Temporal pattern deviation
    """
    
    def __init__(
        self,
        contamination: float = 0.05,
        zscore_threshold: float = 3.0,
        iqr_multiplier: float = 1.5,
    ):
        self.contamination = contamination
        self.zscore_threshold = zscore_threshold
        self.iqr_multiplier = iqr_multiplier
        
        self.baseline_stats: Dict[str, Dict] = {}
        self.is_fitted = False
        
        # Columns to monitor
        self.monitored_cols = [
            "aqi", "pm25", "pm10", "no2", "o3", "co", "so2",
            "temperature", "humidity", "wind_speed"
        ]
    
    def fit(self, historical_data: pd.DataFrame):
        """
        Learn baseline statistics from historical data.
        
        Args:
            historical_data: DataFrame with timestamp index
        """
        logger.info("Fitting anomaly detector baseline...")
        
        for col in self.monitored_cols:
            if col not in historical_data.columns:
                continue
            
            values = historical_data[col].dropna()
            if len(values) < 10:
                continue
            
            # Basic stats
            mean = values.mean()
            std = values.std()
            
            # Robust stats (less sensitive to outliers)
            q1, median, q3 = values.quantile([0.25, 0.5, 0.75])
            iqr = q3 - q1
            
            # Hourly pattern (if enough data)
            hourly_means = {}
            if hasattr(historical_data.index, 'hour'):
                hourly_means = values.groupby(historical_data.index.hour).mean().to_dict()
            
            self.baseline_stats[col] = {
                "mean": mean,
                "std": std,
                "median": median,
                "q1": q1,
                "q3": q3,
                "iqr": iqr,
                "min": values.min(),
                "max": values.max(),
                "hourly_means": hourly_means,
            }
        
        self.is_fitted = True
        logger.info(f"Baseline fitted for {len(self.baseline_stats)} features")
    
    def detect(
        self,
        reading: Dict[str, Any],
        context: Optional[pd.DataFrame] = None,
    ) -> AnomalyResult:
        """
        Check if a single reading is anomalous.
        
        Args:
            reading: Dictionary with sensor reading values
            context: Optional recent readings for temporal context
        
        Returns:
            AnomalyResult with detection details
        """
        if not self.is_fitted:
            # Use default thresholds
            return self._detect_with_defaults(reading)
        
        anomaly_signals = []
        scores = []
        contributing = []
        
        for col in self.monitored_cols:
            value = reading.get(col)
            if value is None or col not in self.baseline_stats:
                continue
            
            stats = self.baseline_stats[col]
            
            # 1. Z-score check
            if stats["std"] > 0:
                zscore = abs(value - stats["mean"]) / stats["std"]
                if zscore > self.zscore_threshold:
                    anomaly_signals.append(("zscore", col, zscore))
                    scores.append(min(1.0, zscore / 5.0))
                    contributing.append(col)
            
            # 2. IQR check
            iqr_lower = stats["q1"] - self.iqr_multiplier * stats["iqr"]
            iqr_upper = stats["q3"] + self.iqr_multiplier * stats["iqr"]
            if value < iqr_lower or value > iqr_upper:
                deviation = max(abs(value - iqr_lower), abs(value - iqr_upper))
                iqr_score = deviation / max(stats["iqr"], 1)
                anomaly_signals.append(("iqr", col, iqr_score))
                scores.append(min(1.0, iqr_score / 3.0))
                if col not in contributing:
                    contributing.append(col)
            
            # 3. Extreme value check (beyond historical range)
            if value > stats["max"] * 1.5 or value < stats["min"] * 0.5:
                anomaly_signals.append(("extreme", col, value))
                scores.append(0.8)
                if col not in contributing:
                    contributing.append(col)
        
        # 4. Temporal pattern check (if context provided)
        if context is not None and len(context) > 3:
            temporal_score = self._check_temporal_pattern(reading, context)
            if temporal_score > 0.5:
                anomaly_signals.append(("temporal", "pattern", temporal_score))
                scores.append(temporal_score)
        
        # Aggregate results
        is_anomaly = len(anomaly_signals) >= 2 or (len(scores) > 0 and max(scores) > 0.7)
        avg_score = np.mean(scores) if scores else 0.0
        
        # Determine anomaly type
        anomaly_type = self._classify_anomaly_type(reading, anomaly_signals)
        
        # Generate explanation
        explanation = self._generate_explanation(anomaly_signals, reading, contributing)
        
        return AnomalyResult(
            is_anomaly=is_anomaly,
            anomaly_score=float(avg_score),
            confidence=min(0.95, 0.5 + len(anomaly_signals) * 0.15),
            anomaly_type=anomaly_type,
            contributing_features=contributing,
            explanation=explanation,
        )
    
    def _detect_with_defaults(self, reading: Dict[str, Any]) -> AnomalyResult:
        """Detect anomalies using absolute thresholds when not fitted."""
        
        # Default absolute thresholds
        thresholds = {
            "aqi": (0, 400),
            "pm25": (0, 300),
            "pm10": (0, 500),
            "no2": (0, 200),
            "o3": (0, 200),
            "co": (0, 15),
            "so2": (0, 150),
            "temperature": (-10, 50),
            "humidity": (0, 100),
        }
        
        violations = []
        for col, (low, high) in thresholds.items():
            value = reading.get(col)
            if value is not None and (value < low or value > high * 1.5):
                violations.append(col)
        
        is_anomaly = len(violations) > 0
        
        return AnomalyResult(
            is_anomaly=is_anomaly,
            anomaly_score=min(1.0, len(violations) * 0.3),
            confidence=0.6,
            anomaly_type="threshold_breach" if is_anomaly else "normal",
            contributing_features=violations,
            explanation=f"Values outside expected ranges: {', '.join(violations)}" if violations else "All values within normal ranges"
        )
    
    def _check_temporal_pattern(
        self, reading: Dict, context: pd.DataFrame
    ) -> float:
        """Check for sudden changes from recent pattern."""
        aqi = reading.get("aqi")
        if aqi is None or "aqi" not in context.columns:
            return 0.0
        
        recent_aqi = context["aqi"].tail(6).values
        if len(recent_aqi) < 3:
            return 0.0
        
        recent_mean = np.mean(recent_aqi)
        recent_std = np.std(recent_aqi) or 10  # Default std if all same
        
        change = abs(aqi - recent_mean)
        temporal_zscore = change / recent_std
        
        return min(1.0, temporal_zscore / 4.0)
    
    def _classify_anomaly_type(
        self, reading: Dict, signals: List[Tuple]
    ) -> str:
        """Classify the type of anomaly detected."""
        if not signals:
            return "normal"
        
        # Check for spike (sudden increase)
        aqi = reading.get("aqi", 0)
        pm25 = reading.get("pm25", 0)
        
        if "aqi" in self.baseline_stats:
            baseline_aqi = self.baseline_stats["aqi"]["median"]
            if aqi > baseline_aqi * 1.5:
                return "spike"
            elif aqi < baseline_aqi * 0.5:
                return "drop"
        
        # Check for specific patterns
        signal_types = [s[0] for s in signals]
        if "temporal" in signal_types:
            return "pattern_break"
        if "extreme" in signal_types:
            return "extreme_value"
        
        return "deviation"
    
    def _generate_explanation(
        self,
        signals: List[Tuple],
        reading: Dict,
        contributing: List[str],
    ) -> str:
        """Generate human-readable anomaly explanation."""
        if not signals:
            return "No anomalies detected. All values within expected ranges."
        
        parts = ["Anomaly detected: "]
        
        # Group signals by type
        zscore_signals = [s for s in signals if s[0] == "zscore"]
        iqr_signals = [s for s in signals if s[0] == "iqr"]
        extreme_signals = [s for s in signals if s[0] == "extreme"]
        temporal_signals = [s for s in signals if s[0] == "temporal"]
        
        if extreme_signals:
            cols = [s[1] for s in extreme_signals]
            parts.append(f"Extreme values in {', '.join(cols)}. ")
        
        if zscore_signals:
            details = [f"{s[1]} (z={s[2]:.1f}σ)" for s in zscore_signals[:3]]
            parts.append(f"Statistical outliers: {', '.join(details)}. ")
        
        if temporal_signals:
            parts.append("Sudden deviation from recent pattern. ")
        
        # Add context on main contributors
        if "aqi" in contributing:
            aqi = reading.get("aqi", 0)
            parts.append(f"AQI={aqi:.0f}. ")
        
        if "pm25" in contributing:
            pm25 = reading.get("pm25", 0)
            parts.append(f"PM2.5={pm25:.1f}µg/m³. ")
        
        return "".join(parts)
    
    def get_anomaly_summary(
        self,
        readings: List[Dict],
        window_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Summarize anomalies over a time window.
        
        Args:
            readings: List of sensor readings
            window_hours: Analysis window
        
        Returns:
            Summary statistics and patterns
        """
        results = [self.detect(r) for r in readings]
        anomalies = [r for r in results if r.is_anomaly]
        
        # Feature contribution counts
        feature_counts: Dict[str, int] = {}
        for a in anomalies:
            for f in a.contributing_features:
                feature_counts[f] = feature_counts.get(f, 0) + 1
        
        # Anomaly type distribution
        type_counts: Dict[str, int] = {}
        for a in anomalies:
            type_counts[a.anomaly_type] = type_counts.get(a.anomaly_type, 0) + 1
        
        return {
            "window_hours": window_hours,
            "total_readings": len(readings),
            "anomaly_count": len(anomalies),
            "anomaly_rate": len(anomalies) / max(len(readings), 1),
            "avg_anomaly_score": np.mean([a.anomaly_score for a in anomalies]) if anomalies else 0,
            "most_anomalous_features": sorted(
                feature_counts.items(), key=lambda x: -x[1]
            )[:5],
            "anomaly_type_distribution": type_counts,
        }


class StatisticalAnomalyDetector:
    """
    Simple statistical anomaly detection using moving statistics.
    Useful for real-time streaming detection.
    """
    
    def __init__(self, window_size: int = 24):
        self.window_size = window_size
        self.history: Dict[str, List[float]] = {}
    
    def update_and_detect(
        self, col: str, value: float, zscore_threshold: float = 3.0
    ) -> Tuple[bool, float]:
        """
        Update history and check for anomaly in streaming fashion.
        
        Args:
            col: Feature name
            value: New value
            zscore_threshold: Z-score threshold for anomaly
        
        Returns:
            Tuple of (is_anomaly, anomaly_score)
        """
        if col not in self.history:
            self.history[col] = []
        
        self.history[col].append(value)
        
        # Keep only window_size values
        if len(self.history[col]) > self.window_size:
            self.history[col] = self.history[col][-self.window_size:]
        
        # Need minimum history
        if len(self.history[col]) < 5:
            return False, 0.0
        
        # Calculate rolling statistics (excluding current value)
        historical = self.history[col][:-1]
        mean = np.mean(historical)
        std = np.std(historical) or 1.0
        
        zscore = abs(value - mean) / std
        is_anomaly = zscore > zscore_threshold
        score = min(1.0, zscore / 5.0)
        
        return is_anomaly, score
