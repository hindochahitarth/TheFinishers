"""
Data Pipeline: Ingestion Scheduler
Runs periodic jobs to fetch live environmental data and persist it.
Uses APScheduler for background job scheduling.
"""

import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.sensor_reading import SensorReading
from app.models.alert import Alert as AlertModel
from app.models.recommendation import Recommendation
from app.services import data_fetcher, aqi_calculator, alert_engine, compliance_checker, recommendation_engine
from app.services.cache_service import cache_set, publish_event, key_current_conditions


async def ingest_environmental_data():
    """
    Main ingestion job: fetch → compute → persist → cache → broadcast.
    Runs every INGESTION_INTERVAL_MINUTES minutes.
    """
    logger.info(f"[{datetime.utcnow().isoformat()}] Starting data ingestion job...")
    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import select
            from app.models.location import Location

            # Get all active locations
            result = await db.execute(select(Location).where(Location.is_active == True))
            locations = result.scalars().all()

            if not locations:
                # Bootstrap default location
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
                locations = [loc]

            for loc in locations:
                try:
                    # Fetch from all sources in parallel
                    weather, aq, traffic = await asyncio.gather(
                        data_fetcher.fetch_weather(loc.latitude, loc.longitude),
                        data_fetcher.fetch_air_quality(loc.latitude, loc.longitude),
                        data_fetcher.fetch_traffic(loc.latitude, loc.longitude),
                    )

                    # Compute AQI
                    aqi_val, aqi_cat, dominant = aqi_calculator.compute_aqi(
                        pm25=aq.get("pm25"), pm10=aq.get("pm10"),
                        no2=aq.get("no2"), o3=aq.get("o3"),
                        co=aq.get("co"), so2=aq.get("so2"),
                    )

                    # Persist reading
                    reading = SensorReading(
                        location_id=loc.id,
                        timestamp=datetime.utcnow(),
                        aqi=aqi_val,
                        aqi_category=aqi_cat,
                        dominant_pollutant=dominant,
                        **{k: v for k, v in aq.items()},
                        **{k: v for k, v in weather.items()},
                        **{k: v for k, v in traffic.items()},
                        data_quality_score=1.0,
                        source="OpenAQ",
                    )
                    db.add(reading)

                    # Generate and store alerts
                    alerts_data = alert_engine.check_pollutant_alerts(aq, aqi_val, loc.id)
                    for a in alerts_data:
                        db.add(AlertModel(**a))

                    # Recommendations
                    recs = recommendation_engine.generate_recommendations(
                        aqi=aqi_val, aqi_category=aqi_cat, dominant_pollutant=dominant,
                        traffic_density_index=traffic.get("traffic_density_index"),
                        location_id=loc.id,
                    )
                    for r in recs:
                        db.add(Recommendation(
                            **{k: v for k, v in r.items() if k not in ["desc", "created_at"]},
                            description=r.get("desc", r.get("description", "")),
                        ))

                    await db.commit()

                    # Cache and broadcast
                    snapshot = {
                        "location_id": loc.id, "city": loc.city,
                        "aqi": aqi_val, "aqi_category": aqi_cat,
                        "dominant_pollutant": dominant,
                        "pm25": aq.get("pm25"), "pm10": aq.get("pm10"),
                        "no2": aq.get("no2"), "o3": aq.get("o3"),
                        "temperature": weather.get("temperature"),
                        "humidity": weather.get("humidity"),
                        "wind_speed": weather.get("wind_speed"),
                        "traffic_density_index": traffic.get("traffic_density_index"),
                        "congestion_level": traffic.get("congestion_level"),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    await cache_set(key_current_conditions(loc.id), snapshot, ttl=600)
                    await publish_event("greenpulse:live", {"type": "update", "data": snapshot})
                    logger.info(f"✅ Ingested data for {loc.city}: AQI={aqi_val}, Category={aqi_cat}")

                except Exception as e:
                    logger.error(f"❌ Ingestion failed for {loc.city}: {e}")

        except Exception as e:
            logger.error(f"❌ Scheduler job failed: {e}")
            await db.rollback()


def start_scheduler():
    """Start the APScheduler background process."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        ingest_environmental_data,
        trigger=IntervalTrigger(minutes=settings.ingestion_interval_minutes),
        id="ingest_environmental_data",
        name="Environmental Data Ingestion",
        replace_existing=True,
        misfire_grace_time=60,
    )
    scheduler.start()
    logger.info(f"🚀 Scheduler started — running every {settings.ingestion_interval_minutes} minutes")
    return scheduler


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    scheduler = start_scheduler()

    async def main():
        # Run immediate first ingestion
        await ingest_environmental_data()
        # Keep running
        try:
            while True:
                await asyncio.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
            logger.info("Scheduler stopped")

    asyncio.run(main())
