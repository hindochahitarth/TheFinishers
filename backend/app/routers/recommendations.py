"""
Router: Recommendations — Environmental action recommendations
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.recommendation import Recommendation

router = APIRouter()


@router.get("/", summary="Get environmental recommendations")
async def get_recommendations(
    location_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None, description="health/traffic/industrial/policy"),
    priority: Optional[str] = Query(None, description="Low/Medium/High/Urgent"),
    hours: int = Query(24),
    db: AsyncSession = Depends(get_db),
):
    from_dt = datetime.utcnow() - timedelta(hours=hours)
    query = select(Recommendation).where(Recommendation.created_at >= from_dt)
    if location_id:
        query = query.where(Recommendation.location_id == location_id)
    if category:
        query = query.where(Recommendation.category == category)
    if priority:
        query = query.where(Recommendation.priority == priority)
    query = query.order_by(desc(Recommendation.created_at)).limit(50)
    result = await db.execute(query)
    recs = result.scalars().all()

    return {
        "recommendations": [
            {
                "id": r.id, "category": r.category, "priority": r.priority,
                "title": r.title, "description": r.description,
                "action_steps": r.action_steps, "affected_population": r.affected_population,
                "expected_impact": r.expected_impact, "time_horizon": r.time_horizon,
                "confidence_score": r.confidence_score,
                "created_at": r.created_at.isoformat(),
            }
            for r in recs
        ],
        "total": len(recs),
        "location_id": location_id,
    }
