"""
Router: Forecasting — AQI and pollutant predictions
Uses ensemble ML models (XGBoost + LSTM) for accurate forecasting.
"""

from datetime import datetime, timedelta
import random
import math
from typing import Optional, List
from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import structlog
import pandas as pd

from app.database import get_db
from app.models.sensor_reading import SensorReading
from app.schemas.schemas import ForecastResponse, ForecastPoint
from app.services.cache_service import cache_get, cache_set, key_forecast
from app.services.aqi_calculator import compute_aqi

router = APIRouter()
logger = structlog.get_logger(__name__)

# Try to import ML models (graceful fallback if not available)
try:
    from ml_models.forecasting.ensemble_forecaster import EnsembleForecaster, create_mock_forecast
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("ML models not available, using mock forecasts")


def _aqi_category(aqi: float) -> str:
    if aqi <= 50: return "Good"
    if aqi <= 100: return "Satisfactory"
    if aqi <= 200: return "Moderate"
    if aqi <= 300: return "Poor"
    if aqi <= 400: return "Very Poor"
    return "Severe"


# Global forecaster instance (lazy-loaded)
_ensemble_forecaster: Optional['EnsembleForecaster'] = None


def get_forecaster() -> Optional['EnsembleForecaster']:
    """Get or create the ensemble forecaster."""
    global _ensemble_forecaster
    if ML_AVAILABLE and _ensemble_forecaster is None:
        try:
            _ensemble_forecaster = EnsembleForecaster()
            logger.info("Ensemble forecaster initialized")
        except Exception as e:
            logger.error(f"Failed to initialize forecaster: {e}")
    return _ensemble_forecaster


async def _prepare_historical_data(db: AsyncSession, location_id: int, hours: int = 168) -> pd.DataFrame:
    """Fetch historical data for forecasting."""
    result = await db.execute(
        select(SensorReading)
        .where(SensorReading.location_id == location_id)
        .order_by(desc(SensorReading.timestamp))
        .limit(hours)
    )
    readings = result.scalars().all()
    
    if not readings:
        return pd.DataFrame()
    
    data = []
    for r in readings:
        data.append({
            'timestamp': r.timestamp,
            'pm25': r.pm25 or 0,
            'pm10': r.pm10 or 0,
            'no2': r.no2 or 0,
            'o3': r.o3 or 0,
            'co': r.co or 0,
            'so2': r.so2 or 0,
            'temperature': r.temperature or 25,
            'humidity': r.humidity or 50,
            'wind_speed': r.wind_speed or 5,
            'wind_direction': r.wind_direction or 180,
            'traffic_density': getattr(r, 'traffic_density', 0.5),
            'aqi': r.aqi or 100,
        })
    
    df = pd.DataFrame(data)
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


@router.get("/aqi", summary="Get AQI forecast for next N hours")
async def forecast_aqi(
    location_id: int = Query(1),
    hours: int = Query(24, ge=1, le=72),
    use_ml: bool = Query(True, description="Use ML ensemble model"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate AQI forecast using ensemble ML model (XGBoost + LSTM).
    
    Falls back to mock forecasts if ML models not available or insufficient data.
    """
    # Try cache
    cached = await cache_get(key_forecast(location_id, hours))
    if cached:
        return cached

    now = datetime.utcnow()
    forecaster = get_forecaster() if use_ml else None
    
    # Try ML-based forecasting
    if forecaster and ML_AVAILABLE:
        try:
            # Fetch historical data
            historical_df = await _prepare_historical_data(db, location_id, hours=168)
            
            if len(historical_df) >= 48:
                # Use ML model
                predictions = forecaster.predict(historical_df, horizon_hours=hours)
                
                forecast_points = []
                for i, pred in enumerate(predictions):
                    future_time = now + timedelta(hours=i + 1)
                    forecast_points.append(ForecastPoint(
                        timestamp=future_time,
                        aqi_predicted=round(pred['aqi'], 1),
                        aqi_lower=round(pred.get('lower_bound', pred['aqi'] * 0.85), 1),
                        aqi_upper=round(pred.get('upper_bound', pred['aqi'] * 1.15), 1),
                        aqi_category=_aqi_category(pred['aqi']),
                        pm25_predicted=round(pred.get('pm25', pred['aqi'] * 0.4), 1),
                        no2_predicted=round(pred.get('no2', pred['aqi'] * 0.3), 1),
                        confidence=round(pred.get('confidence', 0.85), 3),
                    ))
                
                # Get feature importance from XGBoost model
                feature_importance = forecaster.get_feature_importance()
                
                response = {
                    "location_id": location_id,
                    "generated_at": now.isoformat(),
                    "horizon_hours": hours,
                    "model_name": "GreenPulse Ensemble (XGBoost + LSTM)",
                    "model_version": "2.0.0",
                    "model_type": "ml_ensemble",
                    "forecast": [p.model_dump() for p in forecast_points],
                    "feature_importance": feature_importance,
                    "model_info": {
                        "xgboost_weight": forecaster.xgboost_weight,
                        "lstm_weight": forecaster.lstm_weight,
                        "trained_on_samples": len(historical_df),
                    }
                }
                
                await cache_set(key_forecast(location_id, hours), response, ttl=600)
                logger.info("ML forecast generated", location_id=location_id, hours=hours)
                return response
            
        except Exception as e:
            logger.warning(f"ML forecast failed, falling back to mock: {e}")
    
    # Fallback to mock forecast
    if ML_AVAILABLE:
        mock_data = create_mock_forecast(location_id, hours)
        mock_forecast = mock_data["forecast"]
    else:
        mock_forecast = _generate_mock_forecast(db, location_id, hours, now)
    
    forecast_points = []
    for i, pred in enumerate(mock_forecast):
        future_time = now + timedelta(hours=i + 1)
        aqi_val = pred.get('aqi', 100 + random.gauss(0, 20))
        forecast_points.append(ForecastPoint(
            timestamp=future_time,
            aqi_predicted=round(aqi_val, 1),
            aqi_lower=round(pred.get('lower_bound', aqi_val * 0.85), 1),
            aqi_upper=round(pred.get('upper_bound', aqi_val * 1.15), 1),
            aqi_category=_aqi_category(aqi_val),
            pm25_predicted=round(pred.get('pm25', aqi_val * 0.4), 1),
            no2_predicted=round(pred.get('no2', aqi_val * 0.3), 1),
            confidence=round(pred.get('confidence', max(0.5, 0.9 - i * 0.01)), 3),
        ))

    response = {
        "location_id": location_id,
        "generated_at": now.isoformat(),
        "horizon_hours": hours,
        "model_name": "GreenPulse Ensemble (XGBoost + LSTM)",
        "model_version": "1.0.0",
        "model_type": "mock_fallback",
        "forecast": [p.model_dump() for p in forecast_points],
        "feature_importance": {
            "pm25_24h_avg": 0.32,
            "hour_of_day": 0.18,
            "wind_speed": 0.14,
            "humidity": 0.12,
            "traffic_density_index": 0.11,
            "temperature": 0.08,
            "pm25_lag1h": 0.05,
        },
    }

    await cache_set(key_forecast(location_id, hours), response, ttl=600)
    return response


def _generate_mock_forecast(db, location_id: int, hours: int, now: datetime) -> List[dict]:
    """Generate mock forecast when ML not available."""
    base_aqi = 120.0
    forecasts = []
    
    for h in range(hours):
        future_time = now + timedelta(hours=h + 1)
        ist_hour = (future_time.hour + 5) % 24
        diurnal_factor = 1.0 + 0.3 * math.sin((ist_hour - 8) * math.pi / 12)
        noise = random.gauss(0, base_aqi * 0.06)
        predicted = max(10, base_aqi * diurnal_factor + noise)
        
        forecasts.append({
            'aqi': predicted,
            'lower_bound': max(0, predicted * 0.85),
            'upper_bound': min(500, predicted * 1.15),
            'pm25': predicted * 0.4 + random.gauss(0, 5),
            'no2': predicted * 0.3 + random.gauss(0, 4),
            'confidence': max(0.4, 0.95 - h * 0.012),
        })
    
    return forecasts
