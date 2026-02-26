"""
Change Point Detection
Identifies structural breaks and regime changes in environmental time series.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ChangePoint:
    """Detected change point information."""
    timestamp: datetime
    index: int
    change_magnitude: float
    change_direction: str  # increase, decrease
    affected_metrics: List[str]
    confidence: float
    explanation: str


class ChangePointDetector:
    """
    Detects change points (structural breaks) in time series.
    Uses combination of:
    1. PELT (Pruned Exact Linear Time) algorithm via ruptures
    2. Bayesian online change point detection
    3. CUSUM (cumulative sum) control charts
    """
    
    def __init__(
        self,
        min_segment_size: int = 6,  # Minimum points between change points
        penalty_multiplier: float = 3.0,
        cusum_threshold: float = 5.0,
    ):
        self.min_segment_size = min_segment_size
        self.penalty_multiplier = penalty_multiplier
        self.cusum_threshold = cusum_threshold
    
    def detect_ruptures(
        self,
        data: pd.DataFrame,
        column: str = "aqi",
        model: str = "rbf",  # rbf, l2, l1
        n_changepoints: Optional[int] = None,
    ) -> List[ChangePoint]:
        """
        Detect change points using ruptures library (PELT algorithm).
        
        Args:
            data: Time series DataFrame with timestamp index
            column: Column to analyze
            model: Cost function model (rbf=kernel, l2=mean shift, l1=median shift)
            n_changepoints: Fixed number of breaks (None for automatic)
        
        Returns:
            List of ChangePoint objects
        """
        try:
            import ruptures as rpt
        except ImportError:
            logger.warning("ruptures not installed, using fallback method")
            return self._detect_simple_changepoints(data, column)
        
        if column not in data.columns:
            return []
        
        signal = data[column].dropna().values
        if len(signal) < self.min_segment_size * 2:
            return []
        
        # Penalty for PELT (controls sensitivity)
        penalty = np.log(len(signal)) * self.penalty_multiplier * np.std(signal)
        
        # Select model
        if model == "rbf":
            algo = rpt.Pelt(model="rbf", min_size=self.min_segment_size).fit(signal)
        elif model == "l2":
            algo = rpt.Pelt(model="l2", min_size=self.min_segment_size).fit(signal)
        else:
            algo = rpt.Pelt(model="l1", min_size=self.min_segment_size).fit(signal)
        
        # Detect change points
        if n_changepoints is not None:
            breakpoints = algo.predict(n_bkps=n_changepoints)
        else:
            breakpoints = algo.predict(pen=penalty)
        
        # Convert to ChangePoint objects
        change_points = []
        timestamps = data[column].dropna().index
        
        for idx in breakpoints[:-1]:  # Last point is always end of signal
            if idx >= len(timestamps):
                continue
            
            # Calculate change magnitude
            before = signal[max(0, idx - self.min_segment_size):idx]
            after = signal[idx:min(len(signal), idx + self.min_segment_size)]
            
            if len(before) == 0 or len(after) == 0:
                continue
            
            magnitude = np.mean(after) - np.mean(before)
            direction = "increase" if magnitude > 0 else "decrease"
            
            # Confidence based on magnitude vs noise
            noise = np.std(signal)
            confidence = min(0.95, abs(magnitude) / (noise * 2)) if noise > 0 else 0.5
            
            change_points.append(ChangePoint(
                timestamp=timestamps[idx],
                index=idx,
                change_magnitude=float(magnitude),
                change_direction=direction,
                affected_metrics=[column],
                confidence=float(confidence),
                explanation=self._generate_change_explanation(column, magnitude, direction, timestamps[idx])
            ))
        
        return change_points
    
    def _detect_simple_changepoints(
        self,
        data: pd.DataFrame,
        column: str,
    ) -> List[ChangePoint]:
        """Fallback change point detection using rolling statistics."""
        if column not in data.columns:
            return []
        
        series = data[column].dropna()
        if len(series) < 10:
            return []
        
        # Rolling mean and std
        window = max(3, len(series) // 10)
        rolling_mean = series.rolling(window=window, center=True).mean()
        rolling_std = series.rolling(window=window, center=True).std()
        
        # Detect significant shifts
        change_points = []
        zscore_diff = rolling_mean.diff().abs() / rolling_std.shift()
        
        # Find peaks in zscore_diff
        threshold = 2.0
        for i, (ts, zscore) in enumerate(zscore_diff.items()):
            if pd.isna(zscore):
                continue
            if zscore > threshold:
                # Check if local maximum
                neighbors = zscore_diff.iloc[max(0, i-2):i+3]
                if zscore >= neighbors.max():
                    magnitude = rolling_mean.iloc[i] - rolling_mean.iloc[max(0, i-window)]
                    direction = "increase" if magnitude > 0 else "decrease"
                    
                    change_points.append(ChangePoint(
                        timestamp=ts,
                        index=i,
                        change_magnitude=float(magnitude),
                        change_direction=direction,
                        affected_metrics=[column],
                        confidence=min(0.9, zscore / 4),
                        explanation=self._generate_change_explanation(column, magnitude, direction, ts)
                    ))
        
        return change_points
    
    def detect_cusum(
        self,
        data: pd.DataFrame,
        column: str = "aqi",
        target: Optional[float] = None,
    ) -> List[ChangePoint]:
        """
        CUSUM (Cumulative Sum) control chart for detecting mean shifts.
        Good for detecting gradual drifts.
        
        Args:
            data: Time series DataFrame
            column: Column to analyze
            target: Target mean (default: historical mean)
        
        Returns:
            List of detected change points
        """
        if column not in data.columns:
            return []
        
        series = data[column].dropna()
        if len(series) < 10:
            return []
        
        # Use historical mean as target
        if target is None:
            target = series.iloc[:len(series)//3].mean()  # Use first third as baseline
        
        sigma = series.std()
        if sigma == 0:
            return []
        
        # CUSUM calculation
        cusum_pos = np.zeros(len(series))
        cusum_neg = np.zeros(len(series))
        
        k = 0.5  # Allowance (slack value)
        
        for i in range(1, len(series)):
            cusum_pos[i] = max(0, cusum_pos[i-1] + (series.iloc[i] - target) / sigma - k)
            cusum_neg[i] = max(0, cusum_neg[i-1] - (series.iloc[i] - target) / sigma - k)
        
        # Detect threshold crossings
        change_points = []
        h = self.cusum_threshold  # Decision threshold
        
        in_alarm_pos = False
        in_alarm_neg = False
        
        for i in range(1, len(series)):
            ts = series.index[i]
            
            # Positive shift detection
            if cusum_pos[i] > h and not in_alarm_pos:
                in_alarm_pos = True
                magnitude = series.iloc[i] - target
                change_points.append(ChangePoint(
                    timestamp=ts,
                    index=i,
                    change_magnitude=float(magnitude),
                    change_direction="increase",
                    affected_metrics=[column],
                    confidence=min(0.9, cusum_pos[i] / (h * 2)),
                    explanation=f"CUSUM detected upward drift in {column} starting at {ts}"
                ))
            elif cusum_pos[i] <= 0:
                in_alarm_pos = False
            
            # Negative shift detection
            if cusum_neg[i] > h and not in_alarm_neg:
                in_alarm_neg = True
                magnitude = series.iloc[i] - target
                change_points.append(ChangePoint(
                    timestamp=ts,
                    index=i,
                    change_magnitude=float(magnitude),
                    change_direction="decrease",
                    affected_metrics=[column],
                    confidence=min(0.9, cusum_neg[i] / (h * 2)),
                    explanation=f"CUSUM detected downward drift in {column} starting at {ts}"
                ))
            elif cusum_neg[i] <= 0:
                in_alarm_neg = False
        
        return change_points
    
    def detect_multivariate(
        self,
        data: pd.DataFrame,
        columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Detect change points across multiple variables.
        Identifies correlated regime changes.
        
        Args:
            data: DataFrame with multiple time series
            columns: Columns to analyze (default: all numeric)
        
        Returns:
            Summary with per-column and combined change points
        """
        if columns is None:
            columns = data.select_dtypes(include=[np.number]).columns.tolist()
        
        all_change_points: Dict[str, List[ChangePoint]] = {}
        
        for col in columns:
            cps = self.detect_ruptures(data, col)
            if cps:
                all_change_points[col] = cps
        
        # Find coincident change points (regime changes)
        regime_changes = self._find_coincident_changes(all_change_points)
        
        return {
            "per_column": all_change_points,
            "regime_changes": regime_changes,
            "summary": {
                "total_change_points": sum(len(v) for v in all_change_points.values()),
                "columns_with_changes": list(all_change_points.keys()),
                "regime_change_count": len(regime_changes),
            }
        }
    
    def _find_coincident_changes(
        self,
        per_column_changes: Dict[str, List[ChangePoint]],
        tolerance_hours: int = 3,
    ) -> List[Dict[str, Any]]:
        """Find change points that occur simultaneously across variables."""
        if not per_column_changes:
            return []
        
        # Collect all change points with timestamps
        all_cps = []
        for col, cps in per_column_changes.items():
            for cp in cps:
                all_cps.append({"column": col, "cp": cp, "ts": cp.timestamp})
        
        if not all_cps:
            return []
        
        # Sort by timestamp
        all_cps.sort(key=lambda x: x["ts"])
        
        # Group nearby change points
        regime_changes = []
        current_group = [all_cps[0]]
        
        for cp_info in all_cps[1:]:
            # Check if within tolerance of current group
            group_end = max(c["ts"] for c in current_group)
            delta = (cp_info["ts"] - group_end).total_seconds() / 3600
            
            if delta <= tolerance_hours:
                current_group.append(cp_info)
            else:
                # Save current group if it spans multiple variables
                if len(set(c["column"] for c in current_group)) >= 2:
                    regime_changes.append(self._summarize_regime_change(current_group))
                current_group = [cp_info]
        
        # Don't forget last group
        if len(set(c["column"] for c in current_group)) >= 2:
            regime_changes.append(self._summarize_regime_change(current_group))
        
        return regime_changes
    
    def _summarize_regime_change(self, group: List[Dict]) -> Dict[str, Any]:
        """Summarize a group of coincident change points."""
        columns = [c["column"] for c in group]
        timestamps = [c["ts"] for c in group]
        magnitudes = [c["cp"].change_magnitude for c in group]
        
        # Determine overall direction
        positive = sum(1 for m in magnitudes if m > 0)
        negative = len(magnitudes) - positive
        
        return {
            "timestamp_range": (min(timestamps), max(timestamps)),
            "affected_columns": list(set(columns)),
            "n_variables": len(set(columns)),
            "overall_direction": "increasing" if positive > negative else "decreasing" if negative > positive else "mixed",
            "avg_magnitude": float(np.mean(np.abs(magnitudes))),
            "details": [
                {"column": c["column"], "magnitude": c["cp"].change_magnitude}
                for c in group
            ],
        }
    
    def _generate_change_explanation(
        self,
        column: str,
        magnitude: float,
        direction: str,
        timestamp: datetime,
    ) -> str:
        """Generate human-readable explanation for change point."""
        direction_word = "increased" if direction == "increase" else "decreased"
        
        if column == "aqi":
            severity = "significant" if abs(magnitude) > 50 else "moderate" if abs(magnitude) > 20 else "minor"
            return f"AQI {direction_word} by {abs(magnitude):.0f} points ({severity} change) at {timestamp}"
        elif column in ["pm25", "pm10"]:
            return f"{column.upper()} concentration {direction_word} by {abs(magnitude):.1f} µg/m³ at {timestamp}"
        elif column in ["no2", "o3", "so2"]:
            return f"{column.upper()} levels {direction_word} by {abs(magnitude):.1f} µg/m³ at {timestamp}"
        elif column == "temperature":
            return f"Temperature {direction_word} by {abs(magnitude):.1f}°C at {timestamp}"
        else:
            return f"{column} {direction_word} by {abs(magnitude):.2f} at {timestamp}"
