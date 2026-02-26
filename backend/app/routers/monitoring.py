"""
Router: Monitoring — current conditions, historical readings, and anomaly detection
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import structlog
import pandas as pd

from app.database import get_db
from app.models.location import Location
from app.models.sensor_reading import SensorReading
from app.models.alert import Alert, AlertStatus
from app.schemas.schemas import CurrentConditionsResponse, HistoryResponse, LocationOut, SensorReadingOut, PollutantData, WeatherData, TrafficData
from app.services import data_fetcher, aqi_calculator, alert_engine, cache_service, compliance_checker, recommendation_engine
from app.models.alert import Alert as AlertModel
from app.models.recommendation import Recommendation
from app.config import settings

router = APIRouter()
logger = structlog.get_logger(__name__)

# Try to import anomaly detection (graceful fallback)
try:
    from ml_models.anomaly_detection.detector import AnomalyDetector
    from ml_models.anomaly_detection.isolation_forest import IsolationForestDetector
    from ml_models.anomaly_detection.change_point import ChangePointDetector
    ANOMALY_DETECTION_AVAILABLE = True
except ImportError:
    ANOMALY_DETECTION_AVAILABLE = False
    logger.warning("Anomaly detection modules not available")

# Global detector instances
_anomaly_detector: Optional['AnomalyDetector'] = None
_isolation_forest: Optional['IsolationForestDetector'] = None
_change_point_detector: Optional['ChangePointDetector'] = None


async def _get_or_create_default_location(db: AsyncSession) -> Location:
    result = await db.execute(select(Location).where(Location.city == settings.default_city).limit(1))
    loc = result.scalar_one_or_none()
    if not loc:
        loc = Location(
            name=f"{settings.default_city} Environmental Station",
            city=settings.default_city,
            country="India",
            country_code=settings.default_country_code,
            latitude=settings.default_lat,
            longitude=settings.default_lon,
        )
        db.add(loc)
        await db.commit()
        await db.refresh(loc)
    return loc


async def _reading_to_schema(r: SensorReading, loc: Location) -> SensorReadingOut:
    return SensorReadingOut(
        id=r.id,
        location_id=r.location_id,
        timestamp=r.timestamp,
        aqi=r.aqi,
        aqi_category=r.aqi_category,
        dominant_pollutant=r.dominant_pollutant,
        pollutants=PollutantData(pm25=r.pm25, pm10=r.pm10, no2=r.no2, o3=r.o3, co=r.co, so2=r.so2, nh3=r.nh3),
        weather=WeatherData(temperature=r.temperature, humidity=r.humidity, wind_speed=r.wind_speed,
                            wind_direction=r.wind_direction, pressure=r.pressure, visibility=r.visibility,
                            uv_index=r.uv_index, cloud_cover=r.cloud_cover, precipitation=r.precipitation,
                            weather_condition=r.weather_condition),
        traffic=TrafficData(traffic_density_index=r.traffic_density_index, congestion_level=r.congestion_level,
                            average_speed_kmh=r.average_speed_kmh),
        is_anomaly=r.is_anomaly,
        anomaly_score=r.anomaly_score,
        data_quality_score=r.data_quality_score,
        source=r.source,
    )


@router.get("/current", summary="Get current environmental conditions")
async def get_current_conditions(
    location_id: Optional[int] = Query(None),
    city: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    # Try cache first
    loc_id = location_id or 1
    cached = await cache_service.cache_get(cache_service.key_current_conditions(loc_id))
    if cached:
        return cached

    loc = await _get_or_create_default_location(db)

    # Fetch live data
    weather = await data_fetcher.fetch_weather(loc.latitude, loc.longitude)
    air_quality = await data_fetcher.fetch_air_quality(loc.latitude, loc.longitude)
    traffic = await data_fetcher.fetch_traffic(loc.latitude, loc.longitude)

    # Compute AQI
    aqi_val, aqi_cat, dominant = aqi_calculator.compute_aqi(
        pm25=air_quality.get("pm25"), pm10=air_quality.get("pm10"),
        no2=air_quality.get("no2"), o3=air_quality.get("o3"),
        co=air_quality.get("co"), so2=air_quality.get("so2"),
    )

    # Persist reading
    reading = SensorReading(
        location_id=loc.id,
        timestamp=datetime.utcnow(),
        aqi=aqi_val,
        aqi_category=aqi_cat,
        dominant_pollutant=dominant,
        **{k: v for k, v in air_quality.items()},
        **{k: v for k, v in weather.items()},
        **{k: v for k, v in traffic.items()},
        data_quality_score=1.0,
        source="OpenAQ",
    )
    db.add(reading)
    await db.commit()
    await db.refresh(reading)

    # Generate and store alerts
    alerts_data = alert_engine.check_pollutant_alerts(air_quality, aqi_val, loc.id)
    for a in alerts_data:
        db.add(AlertModel(**a))

    # Generate recommendations
    recs = recommendation_engine.generate_recommendations(
        aqi=aqi_val, aqi_category=aqi_cat, dominant_pollutant=dominant,
        traffic_density_index=traffic.get("traffic_density_index"), location_id=loc.id,
    )
    for r in recs:
        db.add(Recommendation(**{k: v for k, v in r.items() if k != "desc"}, description=r.get("desc", "")))

    await db.commit()

    # Count active alerts
    alert_count_res = await db.execute(
        select(AlertModel).where(AlertModel.location_id == loc.id, AlertModel.status == AlertStatus.ACTIVE)
    )
    active_alerts = len(alert_count_res.scalars().all())

    # Compliance status
    comp = compliance_checker.assess_compliance(air_quality, loc.id)

    reading_schema = await _reading_to_schema(reading, loc)
    loc_schema = LocationOut.model_validate(loc)

    response = {
        "location": loc_schema.model_dump(),
        "reading": reading_schema.model_dump(),
        "alert_count": active_alerts,
        "compliance_status": comp["risk_level"],
        "retrieved_at": datetime.utcnow().isoformat(),
    }

    await cache_service.cache_set(cache_service.key_current_conditions(loc.id), response, ttl=300)
    await cache_service.publish_event("greenpulse:live", response)
    return response


@router.get("/history", summary="Get historical sensor readings")
async def get_history(
    location_id: int = Query(1),
    hours: int = Query(24, le=720),
    db: AsyncSession = Depends(get_db),
):
    from_dt = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(SensorReading)
        .where(SensorReading.location_id == location_id, SensorReading.timestamp >= from_dt)
        .order_by(desc(SensorReading.timestamp))
        .limit(1000)
    )
    readings = result.scalars().all()
    loc_res = await db.execute(select(Location).where(Location.id == location_id))
    loc = loc_res.scalar_one_or_none()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    schemas = [await _reading_to_schema(r, loc) for r in readings]
    return {
        "location_id": location_id,
        "readings": [s.model_dump() for s in schemas],
        "total": len(schemas),
        "from_dt": from_dt.isoformat(),
        "to_dt": datetime.utcnow().isoformat(),
    }


@router.get("/locations", summary="List all monitoring locations")
async def list_locations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Location).where(Location.is_active == True))
    locs = result.scalars().all()
    return {"locations": [LocationOut.model_validate(l).model_dump() for l in locs]}


@router.get("/anomalies", summary="Detect anomalies in sensor data")
async def detect_anomalies(
    location_id: int = Query(1),
    hours: int = Query(24, le=168),
    pollutant: str = Query("pm25", description="Target pollutant to analyze"),
    db: AsyncSession = Depends(get_db),
):
    """
    Detect anomalies in environmental sensor data using multiple detection methods.
    
    Returns detected anomalies with explanations and severity scores.
    """
    global _anomaly_detector, _isolation_forest
    
    # Fetch historical data
    from_dt = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(SensorReading)
        .where(SensorReading.location_id == location_id, SensorReading.timestamp >= from_dt)
        .order_by(SensorReading.timestamp)
    )
    readings = result.scalars().all()
    
    if len(readings) < 10:
        return {
            "location_id": location_id,
            "period_hours": hours,
            "anomalies": [],
            "message": "Insufficient data for anomaly detection (min 10 readings required)"
        }
    
    # Convert to DataFrame
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
            'aqi': r.aqi or 0,
        })
    df = pd.DataFrame(data)
    
    anomalies = []
    
    if ANOMALY_DETECTION_AVAILABLE:
        try:
            # Statistical detector
            if _anomaly_detector is None:
                _anomaly_detector = AnomalyDetector()
                # Fit on historical baseline if available
                if len(df) >= 24:
                    _anomaly_detector.fit(df[pollutant].values[:len(df)//2])
            
            # Check each reading
            for idx, (_, row) in enumerate(df.iterrows()):
                value = row[pollutant]
                result = _anomaly_detector.detect(value, timestamp=row['timestamp'])
                
                if result.is_anomaly:
                    anomalies.append({
                        "timestamp": row['timestamp'].isoformat(),
                        "pollutant": pollutant,
                        "value": float(value),
                        "anomaly_type": result.anomaly_type,
                        "severity": result.severity,
                        "z_score": result.z_score,
                        "explanation": result.explanation,
                        "detection_method": "statistical"
                    })
            
            # Isolation Forest multivariate detection
            if _isolation_forest is None:
                _isolation_forest = IsolationForestDetector(contamination=0.05)
            
            features = ['pm25', 'pm10', 'no2', 'o3', 'aqi']
            feature_df = df[features].fillna(0)
            
            if len(feature_df) >= 20:
                _isolation_forest.fit(feature_df.values)
                iso_results = _isolation_forest.detect(feature_df.values)
                
                for anomaly_idx in iso_results['anomaly_indices']:
                    if anomaly_idx < len(df):
                        row = df.iloc[anomaly_idx]
                        # Avoid duplicates
                        existing_ts = [a['timestamp'] for a in anomalies]
                        if row['timestamp'].isoformat() not in existing_ts:
                            contributions = iso_results.get('feature_contributions', {})
                            anomalies.append({
                                "timestamp": row['timestamp'].isoformat(),
                                "pollutant": "multivariate",
                                "value": float(row['aqi']),
                                "anomaly_type": "isolation_forest",
                                "severity": "high",
                                "explanation": f"Multivariate anomaly detected across multiple pollutants",
                                "feature_contributions": contributions.get(anomaly_idx, {}),
                                "detection_method": "isolation_forest"
                            })
                            
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            
    else:
        # Simple fallback anomaly detection
        mean_val = df[pollutant].mean()
        std_val = df[pollutant].std()
        
        for _, row in df.iterrows():
            value = row[pollutant]
            z_score = (value - mean_val) / std_val if std_val > 0 else 0
            
            if abs(z_score) > 2.5:
                anomalies.append({
                    "timestamp": row['timestamp'].isoformat(),
                    "pollutant": pollutant,
                    "value": float(value),
                    "anomaly_type": "spike" if z_score > 0 else "drop",
                    "severity": "high" if abs(z_score) > 3 else "medium",
                    "z_score": float(z_score),
                    "explanation": f"Value {value:.1f} is {abs(z_score):.1f} std deviations from mean ({mean_val:.1f})",
                    "detection_method": "simple_zscore"
                })
    
    # Sort by timestamp
    anomalies.sort(key=lambda x: x['timestamp'])
    
    return {
        "location_id": location_id,
        "period_hours": hours,
        "pollutant_analyzed": pollutant,
        "total_readings": len(df),
        "anomalies_detected": len(anomalies),
        "anomalies": anomalies,
        "detection_methods": ["statistical", "isolation_forest"] if ANOMALY_DETECTION_AVAILABLE else ["simple_zscore"],
    }


@router.get("/change-points", summary="Detect regime changes in air quality")
async def detect_change_points(
    location_id: int = Query(1),
    hours: int = Query(168, le=720),
    pollutant: str = Query("aqi", description="Target metric to analyze"),
    db: AsyncSession = Depends(get_db),
):
    """
    Detect significant change points (regime shifts) in environmental data.
    
    Uses PELT algorithm and CUSUM charts for robust detection.
    """
    global _change_point_detector
    
    from_dt = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(SensorReading)
        .where(SensorReading.location_id == location_id, SensorReading.timestamp >= from_dt)
        .order_by(SensorReading.timestamp)
    )
    readings = result.scalars().all()
    
    if len(readings) < 24:
        return {
            "location_id": location_id,
            "period_hours": hours,
            "change_points": [],
            "message": "Insufficient data for change point detection (min 24 readings required)"
        }
    
    # Convert to series
    timestamps = [r.timestamp for r in readings]
    values = [getattr(r, pollutant) or 0 for r in readings]
    
    change_points = []
    
    if ANOMALY_DETECTION_AVAILABLE:
        try:
            if _change_point_detector is None:
                _change_point_detector = ChangePointDetector(min_segment_length=6)
            
            detected = _change_point_detector.detect(values, timestamps=timestamps)
            
            for cp in detected:
                change_points.append({
                    "timestamp": cp.timestamp.isoformat() if cp.timestamp else None,
                    "index": cp.index,
                    "change_type": cp.change_type,
                    "magnitude": cp.magnitude,
                    "confidence": cp.confidence,
                    "before_mean": cp.before_mean,
                    "after_mean": cp.after_mean,
                })
                
        except Exception as e:
            logger.error(f"Change point detection error: {e}")
    else:
        # Simple moving average change detection
        import numpy as np
        values_arr = np.array(values)
        window = min(12, len(values_arr) // 4)
        
        for i in range(window, len(values_arr) - window):
            before_mean = values_arr[i-window:i].mean()
            after_mean = values_arr[i:i+window].mean()
            change = abs(after_mean - before_mean)
            
            if change > values_arr.std() * 1.5:
                change_points.append({
                    "timestamp": timestamps[i].isoformat(),
                    "index": i,
                    "change_type": "increase" if after_mean > before_mean else "decrease",
                    "magnitude": float(change),
                    "confidence": min(0.9, change / (values_arr.std() + 1)),
                    "before_mean": float(before_mean),
                    "after_mean": float(after_mean),
                })
    
    return {
        "location_id": location_id,
        "period_hours": hours,
        "pollutant_analyzed": pollutant,
        "total_readings": len(readings),
        "change_points_detected": len(change_points),
        "change_points": change_points,
    }
