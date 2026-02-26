"""
Environmental Tools for AI Agents
Domain-specific tools for environmental monitoring, analysis, and reasoning.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)


class EnvironmentalTools:
    """
    Collection of environmental monitoring and analysis tools
    for use with LangChain/LangGraph agents.
    """
    
    def __init__(self, db_session=None, config=None):
        self.db_session = db_session
        self.config = config or {}
        self._cache: Dict[str, Any] = {}
    
    async def get_current_conditions(
        self, 
        location_id: int = 1,
        city: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get current environmental conditions for a location.
        
        Args:
            location_id: Database location ID
            city: City name (optional override)
        
        Returns:
            Current AQI, pollutants, weather, and traffic data
        """
        try:
            from app.services import data_fetcher, aqi_calculator
            from app.config import settings
            
            lat = settings.default_lat
            lon = settings.default_lon
            city = city or settings.default_city
            
            weather = await data_fetcher.fetch_weather(lat, lon)
            air_quality = await data_fetcher.fetch_air_quality(lat, lon)
            traffic = await data_fetcher.fetch_traffic(lat, lon)
            
            aqi_val, aqi_cat, dominant = aqi_calculator.compute_aqi(
                pm25=air_quality.get("pm25"),
                pm10=air_quality.get("pm10"),
                no2=air_quality.get("no2"),
                o3=air_quality.get("o3"),
                co=air_quality.get("co"),
                so2=air_quality.get("so2"),
            )
            
            return {
                "status": "success",
                "city": city,
                "timestamp": datetime.utcnow().isoformat(),
                "aqi": aqi_val,
                "aqi_category": aqi_cat,
                "dominant_pollutant": dominant,
                "pollutants": air_quality,
                "weather": weather,
                "traffic": traffic,
            }
        except Exception as e:
            logger.error(f"Error getting current conditions: {e}")
            return {"status": "error", "message": str(e)}
    
    def check_health_risk(
        self,
        aqi: float,
        dominant_pollutant: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Assess health risk based on AQI and pollutant levels.
        
        Args:
            aqi: Current Air Quality Index value
            dominant_pollutant: Main pollutant contributing to AQI
        
        Returns:
            Risk assessment with recommendations
        """
        if aqi <= 50:
            risk_level = "Low"
            general_advice = "Air quality is satisfactory. Outdoor activities are safe for everyone."
            sensitive_advice = "No special precautions needed."
        elif aqi <= 100:
            risk_level = "Moderate"
            general_advice = "Air quality is acceptable. Most people can continue outdoor activities."
            sensitive_advice = "Unusually sensitive individuals should consider reducing prolonged outdoor exertion."
        elif aqi <= 200:
            risk_level = "High"
            general_advice = "Everyone may begin to experience health effects. Reduce prolonged outdoor exertion."
            sensitive_advice = "Children, elderly, and those with respiratory conditions should limit outdoor activity."
        elif aqi <= 300:
            risk_level = "Very High"
            general_advice = "Health alert: everyone may experience more serious health effects. Avoid outdoor exertion."
            sensitive_advice = "Sensitive groups should avoid all outdoor activity. Consider wearing N95 masks if outdoor exposure is necessary."
        else:
            risk_level = "Severe"
            general_advice = "Health emergency: everyone is at risk. Avoid all outdoor activity if possible."
            sensitive_advice = "Everyone should stay indoors with air purification if available. Emergency protocols may be needed."
        
        pollutant_risks = {
            "pm25": "Fine particles can penetrate deep into lungs and bloodstream, causing respiratory and cardiovascular issues.",
            "pm10": "Coarse particles can trigger asthma and aggravate lung conditions.",
            "no2": "Nitrogen dioxide irritates airways and can worsen asthma and increase susceptibility to infections.",
            "o3": "Ground-level ozone causes breathing difficulty, chest pain, and can damage lung tissue.",
            "co": "Carbon monoxide reduces oxygen delivery, causing headaches, dizziness, and can be life-threatening at high levels.",
            "so2": "Sulfur dioxide irritates nose, throat, and airways, especially affecting those with asthma.",
        }
        
        pollutant_specific = ""
        if dominant_pollutant and dominant_pollutant.lower() in pollutant_risks:
            pollutant_specific = pollutant_risks[dominant_pollutant.lower()]
        
        return {
            "aqi": aqi,
            "risk_level": risk_level,
            "general_population_advice": general_advice,
            "sensitive_groups_advice": sensitive_advice,
            "dominant_pollutant_risk": pollutant_specific,
            "assessed_at": datetime.utcnow().isoformat(),
        }
    
    def check_regulatory_compliance(
        self,
        pollutants: Dict[str, float],
        standards: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Check pollutant levels against regulatory standards.
        
        Args:
            pollutants: Dictionary of pollutant concentrations
            standards: Standards to check (WHO, CPCB, NAAQS)
        
        Returns:
            Compliance status per standard with violations
        """
        standards = standards or ["WHO", "CPCB"]
        
        # Regulatory thresholds
        thresholds = {
            "WHO": {
                "pm25": 15.0,  # WHO 2021 guidelines (24h)
                "pm10": 45.0,
                "no2": 25.0,
                "o3": 100.0,  # 8h average
            },
            "CPCB": {
                "pm25": 60.0,  # India NAAQS
                "pm10": 100.0,
                "no2": 80.0,
                "o3": 180.0,
                "co": 4.0,  # mg/m³
                "so2": 80.0,
            },
            "NAAQS": {  # US EPA
                "pm25": 35.0,
                "pm10": 150.0,
                "no2": 100.0,
                "o3": 137.0,
            },
        }
        
        results = {}
        all_violations = []
        
        for standard in standards:
            if standard not in thresholds:
                continue
            
            standard_limits = thresholds[standard]
            violations = []
            is_compliant = True
            
            for pollutant, limit in standard_limits.items():
                value = pollutants.get(pollutant)
                if value is None:
                    continue
                
                if value > limit:
                    is_compliant = False
                    exceeded_by = ((value - limit) / limit) * 100
                    violations.append({
                        "pollutant": pollutant.upper(),
                        "measured": value,
                        "limit": limit,
                        "exceeded_by_percent": round(exceeded_by, 1),
                        "unit": "mg/m³" if pollutant == "co" else "µg/m³",
                    })
                    all_violations.append({
                        "standard": standard,
                        **violations[-1],
                    })
            
            results[standard] = {
                "compliant": is_compliant,
                "violations": violations,
                "violations_count": len(violations),
            }
        
        overall_compliant = all(r["compliant"] for r in results.values())
        
        return {
            "overall_compliant": overall_compliant,
            "per_standard": results,
            "all_violations": all_violations,
            "total_violations": len(all_violations),
            "assessed_at": datetime.utcnow().isoformat(),
        }
    
    def analyze_pollution_sources(
        self,
        dominant_pollutant: str,
        traffic_index: Optional[float] = None,
        wind_speed: Optional[float] = None,
        time_of_day: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Perform root cause analysis for pollution event.
        
        Args:
            dominant_pollutant: Primary pollutant
            traffic_index: 0-10 traffic congestion index
            wind_speed: Wind speed in m/s
            time_of_day: Hour (0-23)
            temperature: Temperature in Celsius
        
        Returns:
            Analysis of likely pollution sources and contributing factors
        """
        pollutant_lower = dominant_pollutant.lower() if dominant_pollutant else ""
        
        sources = []
        contributing_factors = []
        confidence = 0.5  # Base confidence
        
        # Pollutant-specific source analysis
        if pollutant_lower in ["pm25", "pm10"]:
            sources.append({
                "source": "Vehicular emissions",
                "likelihood": "High" if traffic_index and traffic_index > 6 else "Medium",
                "description": "Diesel vehicles, two-wheelers, and traffic congestion contribute significantly to particulate matter."
            })
            sources.append({
                "source": "Construction and dust",
                "likelihood": "Medium",
                "description": "Construction activities and road dust resuspension, especially in dry conditions."
            })
            sources.append({
                "source": "Biomass burning",
                "likelihood": "High" if time_of_day and (time_of_day < 8 or time_of_day > 18) else "Low",
                "description": "Agricultural residue burning, waste incineration, especially in morning/evening."
            })
            sources.append({
                "source": "Industrial emissions",
                "likelihood": "Medium",
                "description": "Thermal power plants, manufacturing units, and brick kilns."
            })
            
        elif pollutant_lower == "no2":
            sources.append({
                "source": "Traffic emissions",
                "likelihood": "Very High",
                "description": "Vehicular combustion is the primary source of NO2, especially during rush hours."
            })
            sources.append({
                "source": "Power generation",
                "likelihood": "Medium",
                "description": "Thermal power plants and industrial boilers."
            })
            confidence = 0.8 if traffic_index and traffic_index > 5 else 0.6
            
        elif pollutant_lower == "o3":
            sources.append({
                "source": "Photochemical formation",
                "likelihood": "High" if time_of_day and 10 <= time_of_day <= 16 else "Low",
                "description": "Ground-level ozone forms from NOx and VOCs reacting in sunlight. Peaks during afternoon."
            })
            sources.append({
                "source": "Precursor emissions (NOx, VOCs)",
                "likelihood": "High",
                "description": "Vehicles, industrial processes, and solvent use emit ozone precursors."
            })
            confidence = 0.75
            
        elif pollutant_lower == "co":
            sources.append({
                "source": "Incomplete combustion",
                "likelihood": "Very High",
                "description": "Vehicular idling, poorly maintained engines, and biomass burning."
            })
            confidence = 0.85 if traffic_index and traffic_index > 6 else 0.65
            
        elif pollutant_lower == "so2":
            sources.append({
                "source": "Industrial emissions",
                "likelihood": "Very High",
                "description": "Coal-burning power plants, refineries, and heavy industry."
            })
            sources.append({
                "source": "Diesel vehicles",
                "likelihood": "Medium",
                "description": "High-sulfur diesel fuel in older vehicles."
            })
            confidence = 0.7
        
        # Contributing factors analysis
        if wind_speed is not None:
            if wind_speed < 2:
                contributing_factors.append({
                    "factor": "Low wind speed",
                    "impact": "High",
                    "description": "Stagnant air prevents pollutant dispersion, causing accumulation."
                })
                confidence += 0.1
            elif wind_speed > 5:
                contributing_factors.append({
                    "factor": "Strong winds",
                    "impact": "Beneficial",
                    "description": "Winds help disperse pollutants and improve air quality."
                })
        
        if temperature is not None:
            if temperature < 15:
                contributing_factors.append({
                    "factor": "Temperature inversion likely",
                    "impact": "High",
                    "description": "Cold surface temperatures can trap pollutants near ground level."
                })
                confidence += 0.1
        
        if time_of_day is not None:
            if 7 <= time_of_day <= 10 or 17 <= time_of_day <= 21:
                contributing_factors.append({
                    "factor": "Rush hour traffic",
                    "impact": "High",
                    "description": "Peak commute times significantly increase vehicular emissions."
                })
        
        return {
            "dominant_pollutant": dominant_pollutant,
            "likely_sources": sources,
            "contributing_factors": contributing_factors,
            "analysis_confidence": min(0.95, confidence),
            "recommendations": self._generate_source_recommendations(pollutant_lower, sources),
            "analyzed_at": datetime.utcnow().isoformat(),
        }
    
    def _generate_source_recommendations(
        self, pollutant: str, sources: List[Dict]
    ) -> List[str]:
        """Generate recommendations based on identified sources."""
        recs = []
        
        source_names = [s["source"].lower() for s in sources if s.get("likelihood") in ["High", "Very High"]]
        
        if "traffic" in str(source_names) or "vehicular" in str(source_names):
            recs.extend([
                "Implement odd-even vehicle scheme or low-emission zones",
                "Promote public transport and carpooling",
                "Enforce vehicle emission standards",
            ])
        
        if "biomass" in str(source_names) or "burning" in str(source_names):
            recs.extend([
                "Enforce ban on biomass and waste burning",
                "Provide alternative crop residue management solutions",
            ])
        
        if "industrial" in str(source_names):
            recs.extend([
                "Inspect industrial emission compliance",
                "Consider temporary shutdown of high-emission units",
            ])
        
        if "construction" in str(source_names) or "dust" in str(source_names):
            recs.extend([
                "Enforce dust suppression measures at construction sites",
                "Increase road washing and sweeping",
            ])
        
        return recs[:5]  # Limit to top 5
    
    def get_forecast_summary(
        self,
        location_id: int = 1,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Get AQI forecast summary for a location.
        
        Args:
            location_id: Location to forecast
            hours: Forecast horizon
        
        Returns:
            Forecast summary with trends and alerts
        """
        try:
            from ml_models.forecasting.ensemble_forecaster import create_mock_forecast
            
            forecast = create_mock_forecast(location_id, hours)
            
            # Analyze forecast trends
            predictions = [f["aqi_predicted"] for f in forecast["forecast"]]
            
            if not predictions:
                return {"status": "error", "message": "No forecast available"}
            
            avg_aqi = sum(predictions) / len(predictions)
            max_aqi = max(predictions)
            min_aqi = min(predictions)
            
            # Find peak time
            max_idx = predictions.index(max_aqi)
            peak_time = forecast["forecast"][max_idx]["timestamp"]
            
            # Trend analysis
            first_half = sum(predictions[:len(predictions)//2]) / max(len(predictions)//2, 1)
            second_half = sum(predictions[len(predictions)//2:]) / max(len(predictions) - len(predictions)//2, 1)
            
            if second_half > first_half * 1.1:
                trend = "deteriorating"
            elif second_half < first_half * 0.9:
                trend = "improving"
            else:
                trend = "stable"
            
            return {
                "status": "success",
                "location_id": location_id,
                "horizon_hours": hours,
                "average_aqi": round(avg_aqi, 1),
                "max_aqi": round(max_aqi, 1),
                "min_aqi": round(min_aqi, 1),
                "peak_pollution_time": peak_time,
                "trend": trend,
                "forecast_points": forecast["forecast"][:6],  # First 6 hours detail
                "generated_at": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Forecast error: {e}")
            return {"status": "error", "message": str(e)}


def create_langchain_tools():
    """
    Create LangChain-compatible tools from EnvironmentalTools.
    Returns list of tools for use with LangChain agents.
    """
    try:
        from langchain_core.tools import tool
    except ImportError:
        logger.warning("LangChain not installed")
        return []
    
    env_tools = EnvironmentalTools()
    
    @tool
    def get_current_aqi() -> str:
        """Get the current Air Quality Index and environmental conditions for the monitored city."""
        import asyncio
        result = asyncio.run(env_tools.get_current_conditions())
        if result.get("status") == "error":
            return f"Error: {result.get('message')}"
        return (
            f"City: {result['city']}\n"
            f"AQI: {result['aqi']} ({result['aqi_category']})\n"
            f"Dominant Pollutant: {result['dominant_pollutant']}\n"
            f"PM2.5: {result['pollutants'].get('pm25', 'N/A')} µg/m³\n"
            f"Temperature: {result['weather'].get('temperature', 'N/A')}°C\n"
            f"Traffic: {result['traffic'].get('congestion_level', 'N/A')}"
        )
    
    @tool  
    def assess_health_risk(aqi: float, dominant_pollutant: str = "pm25") -> str:
        """Assess health risk based on current AQI value and dominant pollutant."""
        result = env_tools.check_health_risk(aqi, dominant_pollutant)
        return (
            f"Risk Level: {result['risk_level']}\n"
            f"General Advice: {result['general_population_advice']}\n"
            f"Sensitive Groups: {result['sensitive_groups_advice']}\n"
            f"Pollutant Risk: {result['dominant_pollutant_risk']}"
        )
    
    @tool
    def check_compliance(pm25: float, pm10: float, no2: float, o3: float) -> str:
        """Check if pollutant levels comply with WHO and CPCB standards."""
        pollutants = {"pm25": pm25, "pm10": pm10, "no2": no2, "o3": o3}
        result = env_tools.check_regulatory_compliance(pollutants)
        
        lines = [f"Overall Compliance: {'Yes' if result['overall_compliant'] else 'NO'}"]
        for std, data in result["per_standard"].items():
            status = "✅ Compliant" if data["compliant"] else f"❌ {data['violations_count']} violations"
            lines.append(f"{std}: {status}")
        
        if result["all_violations"]:
            lines.append("\nViolations:")
            for v in result["all_violations"][:3]:
                lines.append(f"  • {v['pollutant']}: {v['measured']} > {v['limit']} ({v['standard']})")
        
        return "\n".join(lines)
    
    @tool
    def analyze_pollution_source(
        dominant_pollutant: str,
        traffic_index: float = 5.0,
        wind_speed: float = 3.0,
        hour: int = 12,
    ) -> str:
        """Analyze likely sources and root causes of current pollution levels."""
        result = env_tools.analyze_pollution_sources(
            dominant_pollutant, traffic_index, wind_speed, hour
        )
        
        lines = [f"Root Cause Analysis for {dominant_pollutant.upper()}"]
        
        lines.append("\nLikely Sources:")
        for src in result["likely_sources"][:3]:
            lines.append(f"  • {src['source']} (Likelihood: {src['likelihood']})")
            lines.append(f"    {src['description']}")
        
        if result["contributing_factors"]:
            lines.append("\nContributing Factors:")
            for f in result["contributing_factors"]:
                lines.append(f"  • {f['factor']}: {f['description']}")
        
        lines.append(f"\nAnalysis Confidence: {result['analysis_confidence']:.0%}")
        
        return "\n".join(lines)
    
    @tool
    def get_forecast(hours: int = 24) -> str:
        """Get AQI forecast for the next N hours (default 24)."""
        result = env_tools.get_forecast_summary(hours=hours)
        
        if result.get("status") == "error":
            return f"Error: {result.get('message')}"
        
        return (
            f"AQI Forecast ({result['horizon_hours']}h):\n"
            f"  Average: {result['average_aqi']}\n"
            f"  Range: {result['min_aqi']} - {result['max_aqi']}\n"
            f"  Peak: {result['max_aqi']} at {result['peak_pollution_time']}\n"
            f"  Trend: {result['trend'].upper()}"
        )
    
    return [get_current_aqi, assess_health_risk, check_compliance, analyze_pollution_source, get_forecast]
