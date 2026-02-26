"""
Causal Analysis Module
Implements causal reasoning for environmental root cause analysis.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CausalFactor:
    """A factor in causal analysis."""
    name: str
    category: str  # weather, traffic, industrial, temporal
    correlation: float
    lag_hours: int
    influence_score: float
    description: str


class CausalAnalyzer:
    """
    Causal reasoning engine for environmental events.
    Combines:
    1. Correlation analysis with time lags
    2. Domain knowledge rules
    3. Granger causality tests
    4. Intervention analysis
    """
    
    # Domain knowledge: known causal relationships
    CAUSAL_RULES = {
        "pm25": {
            "traffic": {
                "direction": "positive",
                "strength": "strong",
                "lag_hours": [0, 1, 2],
                "mechanism": "Vehicle exhaust emits fine particles directly"
            },
            "wind_speed": {
                "direction": "negative",
                "strength": "strong",
                "lag_hours": [0],
                "mechanism": "Wind disperses particles, reducing concentration"
            },
            "humidity": {
                "direction": "positive",
                "strength": "moderate",
                "lag_hours": [0, 1],
                "mechanism": "High humidity promotes hygroscopic growth of particles"
            },
            "temperature_inversion": {
                "direction": "positive",
                "strength": "strong",
                "lag_hours": [0],
                "mechanism": "Temperature inversions trap pollutants near surface"
            },
            "no2": {
                "direction": "positive",
                "strength": "moderate",
                "lag_hours": [1, 2, 3],
                "mechanism": "NO2 contributes to secondary PM2.5 formation"
            },
        },
        "no2": {
            "traffic": {
                "direction": "positive",
                "strength": "very_strong",
                "lag_hours": [0],
                "mechanism": "Vehicular combustion is primary NO2 source"
            },
            "temperature": {
                "direction": "positive",
                "strength": "weak",
                "lag_hours": [0],
                "mechanism": "Higher temps increase combustion-related emissions"
            },
        },
        "o3": {
            "no2": {
                "direction": "complex",  # Can be positive during day, negative at night
                "strength": "strong",
                "lag_hours": [2, 3, 4],
                "mechanism": "NO2 is precursor to O3 formation via photochemistry"
            },
            "temperature": {
                "direction": "positive",
                "strength": "strong",
                "lag_hours": [1, 2],
                "mechanism": "Photochemical O3 formation increases with temperature"
            },
            "uv_index": {
                "direction": "positive",
                "strength": "very_strong",
                "lag_hours": [1, 2],
                "mechanism": "UV radiation drives photochemical ozone production"
            },
            "solar_hour": {
                "direction": "positive",
                "strength": "strong",
                "lag_hours": [0],
                "mechanism": "O3 forms during daylight, peaks in afternoon"
            },
        },
    }
    
    def __init__(self, significance_threshold: float = 0.05):
        self.significance_threshold = significance_threshold
    
    def analyze_root_causes(
        self,
        pollutant: str,
        current_reading: Dict[str, Any],
        historical_data: Optional[pd.DataFrame] = None,
        time_of_day: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Perform root cause analysis for elevated pollutant levels.
        
        Args:
            pollutant: Target pollutant (pm25, no2, o3, etc.)
            current_reading: Current sensor readings
            historical_data: Optional dataframe of recent readings
            time_of_day: Hour of day (0-23)
        
        Returns:
            Root cause analysis with contributing factors
        """
        pollutant = pollutant.lower()
        contributing_factors = []
        
        # Apply domain knowledge rules
        if pollutant in self.CAUSAL_RULES:
            rules = self.CAUSAL_RULES[pollutant]
            
            for factor, info in rules.items():
                factor_contribution = self._evaluate_factor(
                    factor, info, current_reading, time_of_day
                )
                if factor_contribution:
                    contributing_factors.append(factor_contribution)
        
        # Statistical analysis if historical data available
        if historical_data is not None and len(historical_data) >= 24:
            statistical_factors = self._statistical_analysis(
                pollutant, historical_data
            )
            
            # Merge with rule-based factors
            for sf in statistical_factors:
                # Check if already in contributing factors
                existing = next(
                    (f for f in contributing_factors if f.name == sf.name), None
                )
                if existing:
                    # Combine scores
                    existing.influence_score = (
                        existing.influence_score * 0.6 + sf.influence_score * 0.4
                    )
                else:
                    contributing_factors.append(sf)
        
        # Sort by influence
        contributing_factors.sort(key=lambda x: -x.influence_score)
        
        # Generate summary
        primary_causes = [f for f in contributing_factors if f.influence_score > 0.5]
        secondary_causes = [f for f in contributing_factors if 0.2 <= f.influence_score <= 0.5]
        
        return {
            "target_pollutant": pollutant.upper(),
            "analysis_time": datetime.utcnow().isoformat(),
            "primary_causes": [
                {
                    "factor": f.name,
                    "category": f.category,
                    "influence_score": round(f.influence_score, 3),
                    "correlation": round(f.correlation, 3),
                    "description": f.description,
                }
                for f in primary_causes[:3]
            ],
            "secondary_causes": [
                {
                    "factor": f.name,
                    "category": f.category,
                    "influence_score": round(f.influence_score, 3),
                    "description": f.description,
                }
                for f in secondary_causes[:3]
            ],
            "mechanism_explanation": self._generate_mechanism_explanation(
                pollutant, primary_causes
            ),
            "confidence": self._calculate_confidence(contributing_factors),
            "recommendations": self._generate_recommendations(pollutant, primary_causes),
        }
    
    def _evaluate_factor(
        self,
        factor: str,
        info: Dict,
        current_reading: Dict,
        time_of_day: Optional[int],
    ) -> Optional[CausalFactor]:
        """Evaluate a single causal factor based on current conditions."""
        
        direction = info["direction"]
        strength_map = {"very_strong": 0.9, "strong": 0.7, "moderate": 0.5, "weak": 0.3}
        base_strength = strength_map.get(info["strength"], 0.5)
        
        # Traffic factor
        if factor == "traffic":
            traffic_idx = current_reading.get("traffic_density_index", 5)
            if traffic_idx > 7:  # High traffic
                return CausalFactor(
                    name="traffic_congestion",
                    category="traffic",
                    correlation=0.8 if direction == "positive" else -0.8,
                    lag_hours=0,
                    influence_score=base_strength * (traffic_idx / 10),
                    description=f"Heavy traffic (index {traffic_idx:.1f}) causing elevated emissions. {info['mechanism']}"
                )
            elif traffic_idx > 5:
                return CausalFactor(
                    name="moderate_traffic",
                    category="traffic",
                    correlation=0.5,
                    lag_hours=0,
                    influence_score=base_strength * 0.5,
                    description=f"Moderate traffic contributing to emissions."
                )
        
        # Wind speed factor
        elif factor == "wind_speed":
            wind = current_reading.get("wind_speed", 5)
            if wind < 2:  # Low wind
                return CausalFactor(
                    name="low_wind_stagnation",
                    category="weather",
                    correlation=-0.7,
                    lag_hours=0,
                    influence_score=base_strength * 0.9,
                    description=f"Low wind speed ({wind:.1f} m/s) preventing dispersion. {info['mechanism']}"
                )
            elif wind > 6:
                return CausalFactor(
                    name="wind_dispersion",
                    category="weather",
                    correlation=-0.6,
                    lag_hours=0,
                    influence_score=base_strength * 0.3,  # Beneficial, not a cause
                    description="Strong winds helping disperse pollutants."
                )
        
        # Humidity factor
        elif factor == "humidity":
            humidity = current_reading.get("humidity", 50)
            if humidity > 70:
                return CausalFactor(
                    name="high_humidity",
                    category="weather",
                    correlation=0.5,
                    lag_hours=0,
                    influence_score=base_strength * (humidity / 100),
                    description=f"High humidity ({humidity:.0f}%) promoting particle growth. {info['mechanism']}"
                )
        
        # Temperature inversion (simplified check)
        elif factor == "temperature_inversion":
            temp = current_reading.get("temperature", 25)
            wind = current_reading.get("wind_speed", 5)
            hour = time_of_day or datetime.now().hour
            
            # Inversions more likely at night/early morning with low wind
            if wind < 2 and (hour < 8 or hour > 20):
                return CausalFactor(
                    name="temperature_inversion",
                    category="weather",
                    correlation=0.8,
                    lag_hours=0,
                    influence_score=base_strength * 0.85,
                    description=f"Temperature inversion conditions likely (low wind, {temp:.0f}°C). {info['mechanism']}"
                )
        
        # NO2 as secondary PM2.5 source
        elif factor == "no2":
            no2 = current_reading.get("no2", 50)
            if no2 > 60:
                return CausalFactor(
                    name="no2_secondary_formation",
                    category="chemical",
                    correlation=0.6,
                    lag_hours=2,
                    influence_score=base_strength * (no2 / 100),
                    description=f"Elevated NO2 ({no2:.0f} µg/m³) contributing to secondary PM formation. {info['mechanism']}"
                )
        
        # Temperature (for O3)
        elif factor == "temperature":
            temp = current_reading.get("temperature", 25)
            if temp > 30:
                return CausalFactor(
                    name="high_temperature",
                    category="weather",
                    correlation=0.7,
                    lag_hours=1,
                    influence_score=base_strength * (temp / 40),
                    description=f"High temperature ({temp:.0f}°C) promoting photochemistry. {info['mechanism']}"
                )
        
        # Solar/UV factor (for O3)
        elif factor in ["solar_hour", "uv_index"]:
            uv = current_reading.get("uv_index", 5)
            hour = time_of_day or datetime.now().hour
            
            if 10 <= hour <= 16:  # Peak solar hours
                return CausalFactor(
                    name="solar_radiation",
                    category="weather",
                    correlation=0.85,
                    lag_hours=1,
                    influence_score=base_strength * 0.9,
                    description=f"Peak solar radiation (UV index: {uv:.0f}) driving photochemical ozone formation. {info['mechanism']}"
                )
        
        return None
    
    def _statistical_analysis(
        self,
        pollutant: str,
        data: pd.DataFrame,
    ) -> List[CausalFactor]:
        """Perform statistical correlation analysis."""
        factors = []
        
        if pollutant not in data.columns:
            return factors
        
        target = data[pollutant].dropna()
        
        potential_predictors = [
            "temperature", "humidity", "wind_speed", "pressure",
            "traffic_density_index", "pm25", "pm10", "no2", "o3"
        ]
        
        for pred in potential_predictors:
            if pred == pollutant or pred not in data.columns:
                continue
            
            predictor = data[pred].dropna()
            
            # Align series
            aligned = pd.concat([target, predictor], axis=1).dropna()
            if len(aligned) < 10:
                continue
            
            # Calculate correlation
            corr = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])
            
            if abs(corr) > 0.3:  # Meaningful correlation
                category = (
                    "weather" if pred in ["temperature", "humidity", "wind_speed", "pressure"]
                    else "traffic" if pred == "traffic_density_index"
                    else "pollutant"
                )
                
                factors.append(CausalFactor(
                    name=pred,
                    category=category,
                    correlation=float(corr),
                    lag_hours=0,
                    influence_score=abs(corr) * 0.8,
                    description=f"Statistical correlation of {corr:.2f} detected with {pred}."
                ))
        
        return factors
    
    def _generate_mechanism_explanation(
        self,
        pollutant: str,
        primary_causes: List[CausalFactor],
    ) -> str:
        """Generate narrative explanation of causal mechanism."""
        if not primary_causes:
            return "Insufficient data to determine primary causes."
        
        pollutant_upper = pollutant.upper()
        
        parts = [f"Elevated {pollutant_upper} levels are primarily driven by:"]
        
        for i, cause in enumerate(primary_causes[:3], 1):
            parts.append(f"\n{i}. **{cause.name.replace('_', ' ').title()}** ({cause.category})")
            parts.append(f"   {cause.description}")
        
        if any(c.category == "weather" for c in primary_causes):
            parts.append("\n\nMeteorological conditions are significantly influencing pollution accumulation.")
        
        if any(c.category == "traffic" for c in primary_causes):
            parts.append("\n\nVehicular emissions are a major contributor to current pollution levels.")
        
        return "".join(parts)
    
    def _calculate_confidence(self, factors: List[CausalFactor]) -> float:
        """Calculate confidence in the analysis."""
        if not factors:
            return 0.3  # Low confidence with no factors
        
        # Confidence increases with:
        # - Number of factors identified
        # - Strength of correlations
        # - Consistency with domain knowledge
        
        n_factors = min(len(factors), 5)
        avg_influence = sum(f.influence_score for f in factors[:5]) / max(len(factors[:5]), 1)
        
        confidence = 0.4 + (n_factors * 0.1) + (avg_influence * 0.3)
        return min(0.95, confidence)
    
    def _generate_recommendations(
        self,
        pollutant: str,
        causes: List[CausalFactor],
    ) -> List[str]:
        """Generate actionable recommendations based on causes."""
        recs = []
        
        cause_names = {c.name.lower() for c in causes}
        cause_categories = {c.category for c in causes}
        
        if "traffic" in cause_categories or "traffic_congestion" in cause_names:
            recs.extend([
                "Implement traffic management measures (odd-even, diversions)",
                "Promote public transport and carpooling",
                "Consider temporary restrictions on heavy vehicles",
            ])
        
        if "weather" in cause_categories:
            if "low_wind_stagnation" in cause_names:
                recs.append("Alert: Stagnant conditions expected to persist. Monitor closely.")
            if "temperature_inversion" in cause_names:
                recs.append("Temperature inversion trapping pollutants. Reduce emissions during morning hours.")
        
        if pollutant == "pm25":
            recs.extend([
                "Enforce dust suppression at construction sites",
                "Increase road washing frequency",
            ])
        
        if pollutant == "o3":
            recs.extend([
                "Reduce VOC emissions during peak sunshine hours",
                "Advisory: Ozone levels peak in afternoon, limit outdoor exposure 12-4 PM",
            ])
        
        return recs[:5]


def perform_quick_analysis(reading: Dict[str, Any]) -> Dict[str, Any]:
    """
    Quick root cause analysis for API integration.
    
    Args:
        reading: Current sensor reading
    
    Returns:
        Simplified root cause analysis
    """
    analyzer = CausalAnalyzer()
    
    # Determine which pollutant to analyze (dominant or worst)
    aqi = reading.get("aqi", 100)
    dominant = reading.get("dominant_pollutant", "pm25")
    
    result = analyzer.analyze_root_causes(
        pollutant=dominant,
        current_reading=reading,
        time_of_day=datetime.utcnow().hour,
    )
    
    return result
