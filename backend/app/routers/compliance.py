"""
Router: Compliance — Regulatory compliance checking
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.sensor_reading import SensorReading
from app.services.compliance_checker import assess_compliance
from app.services.cache_service import cache_get, cache_set, key_compliance

router = APIRouter()


@router.get("/assess", summary="Check compliance against WHO, CPCB, and NAAQS")
async def check_compliance(
    location_id: int = Query(1),
    period_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    cached = await cache_get(key_compliance(location_id))
    if cached:
        return cached

    from datetime import timedelta
    from_dt = datetime.utcnow() - timedelta(hours=period_hours)
    result = await db.execute(
        select(SensorReading)
        .where(SensorReading.location_id == location_id, SensorReading.timestamp >= from_dt)
        .order_by(desc(SensorReading.timestamp))
        .limit(200)
    )
    readings = result.scalars().all()

    if not readings:
        return assess_compliance({}, location_id, period_hours)

    # Compute averages for the compliance window
    def avg(attr):
        vals = [getattr(r, attr) for r in readings if getattr(r, attr) is not None]
        return sum(vals) / len(vals) if vals else None

    pollutant_avgs = {
        "pm25": avg("pm25"), "pm10": avg("pm10"),
        "no2": avg("no2"), "o3": avg("o3"),
        "co": avg("co"), "so2": avg("so2"),
    }

    report = assess_compliance(pollutant_avgs, location_id, period_hours)
    await cache_set(key_compliance(location_id), report, ttl=1800)
    return report
