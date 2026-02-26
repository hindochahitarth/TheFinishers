"""
Router: Alerts — alert management
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.alert import Alert, AlertStatus, AlertSeverity

router = APIRouter()


@router.get("/", summary="List recent environmental alerts")
async def list_alerts(
    location_id: int = Query(1),
    hours: int = Query(48),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    from_dt = datetime.utcnow() - timedelta(hours=hours)
    query = select(Alert).where(Alert.location_id == location_id, Alert.triggered_at >= from_dt)
    if severity:
        query = query.where(Alert.severity == severity)
    if status:
        query = query.where(Alert.status == status)
    query = query.order_by(desc(Alert.triggered_at)).limit(100)
    result = await db.execute(query)
    alerts = result.scalars().all()
    active_count = len([a for a in alerts if a.status == AlertStatus.ACTIVE])
    return {
        "alerts": [
            {
                "id": a.id, "title": a.title, "message": a.message,
                "pollutant": a.pollutant, "measured_value": a.measured_value,
                "threshold_value": a.threshold_value, "threshold_standard": a.threshold_standard,
                "severity": a.severity, "status": a.status,
                "is_anomaly_based": a.is_anomaly_based,
                "triggered_at": a.triggered_at.isoformat(),
            }
            for a in alerts
        ],
        "total": len(alerts),
        "active_count": active_count,
    }


@router.patch("/{alert_id}/acknowledge", summary="Acknowledge an alert")
async def acknowledge_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = datetime.utcnow()
    await db.commit()
    return {"message": "Alert acknowledged", "alert_id": alert_id}
