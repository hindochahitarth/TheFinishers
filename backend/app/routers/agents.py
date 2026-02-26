"""
Router: AI Agents — Natural language environmental query interface using LangGraph
"""

import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.schemas import AgentQueryRequest
from app.models.agent_log import AgentLog
from app.services import data_fetcher, aqi_calculator, compliance_checker
from app.models.sensor_reading import SensorReading
from sqlalchemy import select, desc
from app.config import settings
import structlog

router = APIRouter()
logger = structlog.get_logger(__name__)

# Try to import the LangGraph agent (graceful fallback)
try:
    from ai_agents.agent import GreenPulseAgent, AgentSessionManager
    from ai_agents.causal_analysis import CausalAnalyzer
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.warning("LangGraph agent not available, using rule-based fallback")

# Global instances
_agent: Optional['GreenPulseAgent'] = None
_session_manager: Optional['AgentSessionManager'] = None
_causal_analyzer: Optional['CausalAnalyzer'] = None


def get_agent() -> Optional['GreenPulseAgent']:
    """Get or create the GreenPulse agent."""
    global _agent
    if LANGGRAPH_AVAILABLE and _agent is None:
        try:
            # Determine LLM provider from API key
            provider = "openai"
            if settings.llm_api_key:
                if "anthropic" in settings.llm_api_key.lower():
                    provider = "anthropic"
                elif "google" in settings.llm_api_key.lower() or settings.llm_model.startswith("gemini"):
                    provider = "google"
            
            _agent = GreenPulseAgent(
                llm_provider=provider,
                llm_api_key=settings.llm_api_key if settings.llm_api_key and not settings.llm_api_key.startswith("your_") else None,
                llm_model=settings.llm_model,
            )
            logger.info(f"GreenPulse agent initialized with provider: {provider}")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
    return _agent


def get_session_manager() -> Optional['AgentSessionManager']:
    """Get or create the session manager."""
    global _session_manager
    if LANGGRAPH_AVAILABLE and _session_manager is None:
        _session_manager = AgentSessionManager()
    return _session_manager


def get_causal_analyzer() -> Optional['CausalAnalyzer']:
    """Get or create the causal analyzer."""
    global _causal_analyzer
    if LANGGRAPH_AVAILABLE and _causal_analyzer is None:
        _causal_analyzer = CausalAnalyzer()
    return _causal_analyzer


async def _best_llm_response(query: str, context: dict) -> tuple[str, list, list]:
    """
    Use LangGraph agent with GPT-4o / Claude / Gemini if available,
    otherwise return a structured rule-based environmental answer.
    """
    agent = get_agent()
    session_manager = get_session_manager()
    
    if agent and session_manager:
        try:
            # Use LangGraph agent
            session_id = context.get('session_id', str(uuid.uuid4()))
            result = await agent.query(query, session_id=session_id, context=context)
            
            tools_used = result.get('tools_used', [])
            trace = result.get('reasoning_trace', [])
            response = result.get('response', '')
            
            return response, trace, tools_used
        except Exception as e:
            logger.error(f"LangGraph agent failed: {e}")
    
    # Fallback to rule-based
    return await _rule_based_response(query, context)


async def _rule_based_response(query: str, context: dict) -> tuple[str, list, list]:
    """Structured rule-based response when LLM not configured."""
    aqi = context.get("aqi", 100)
    cat = context.get("aqi_category", "Moderate")
    dominant = context.get("dominant_pollutant", "PM2.5")
    temp = context.get("temperature", 25)
    humidity = context.get("humidity", 60)
    comp = context.get("compliance", {})
    who_ok = comp.get("who_compliant", False)
    cpcb_ok = comp.get("cpcb_compliant", False)

    q_lower = query.lower()

    if any(w in q_lower for w in ["aqi", "air quality", "pollution", "safe"]):
        answer = (
            f"**Current Air Quality — {context.get('city', settings.default_city)}**\n\n"
            f"• **AQI**: {aqi:.0f} ({cat})\n"
            f"• **Dominant Pollutant**: {dominant}\n"
            f"• **Weather**: {temp:.1f}°C, {humidity:.0f}% humidity\n\n"
        )
        if aqi > 200:
            answer += "⚠️ **Health Advisory**: Air quality is poor. Vulnerable groups should stay indoors."
        elif aqi > 100:
            answer += "⚠️ **Note**: Sensitive individuals (children, elderly, asthma patients) should limit outdoor exposure."
        else:
            answer += "✅ Air quality is within acceptable range for most people."

    elif any(w in q_lower for w in ["comply", "regulation", "who", "cpcb", "standard", "legal"]):
        answer = (
            f"**Regulatory Compliance Status**\n\n"
            f"• **WHO 2021**: {'✅ Compliant' if who_ok else '❌ Non-Compliant'}\n"
            f"• **CPCB (India)**: {'✅ Compliant' if cpcb_ok else '❌ Non-Compliant'}\n"
            f"• **Risk Level**: {comp.get('risk_level', 'N/A')}\n\n"
        )
        if comp.get("violations"):
            answer += f"• **Violations**: {len(comp['violations'])} standard(s) exceeded"

    elif any(w in q_lower for w in ["forecast", "predict", "tomorrow", "future", "next"]):
        answer = (
            f"**AQI Forecast** (Next 24 Hours)\n\n"
            f"Based on current trends (AQI: {aqi:.0f}, {cat}), expect similar conditions "
            f"with diurnal peaks during morning (8–11 AM IST) and evening rush hours (6–9 PM IST).\n\n"
            f"• **Confidence**: High (short-range)\n"
            f"• **Primary drivers**: {dominant}, wind patterns, traffic\n"
            f"• For a detailed hourly forecast, call the `/api/v1/forecast/aqi` endpoint."
        )

    elif any(w in q_lower for w in ["recommend", "action", "what should", "advice"]):
        answer = (
            f"**Environmental Action Recommendations**\n\n"
            f"Given current AQI of {aqi:.0f} ({cat}):\n"
            f"• {'Stay indoors and avoid strenuous activity' if aqi > 200 else 'Outdoor activities are generally safe, but limit prolonged exertion for sensitive groups.'}\n"
            f"• {'Wear N95 masks if outdoor exposure is unavoidable.' if aqi > 150 else ''}\n"
            f"• Monitor air quality updates every hour during pollution peaks.\n"
            f"• Check `/api/v1/recommendations` for detailed, context-specific action plans."
        )

    else:
        answer = (
            f"**GreenPulse AI Environmental Assistant**\n\n"
            f"I can help with:\n"
            f"• Current air quality and AQI status\n"
            f"• Regulatory compliance (WHO, CPCB, NAAQS)\n"
            f"• 24–72 hour AQI forecasts\n"
            f"• Health recommendations and action plans\n"
            f"• Root cause analysis of pollution events\n\n"
            f"**Current snapshot**: AQI {aqi:.0f} ({cat}) in {context.get('city', settings.default_city)}.\n"
            f"💡 *Add your LLM API key in `.env` (LLM_API_KEY) to enable full GPT-4o powered reasoning.*"
        )

    trace = [
        {"step": 1, "action": "Fetch current environmental data", "result": f"AQI={aqi}, Category={cat}"},
        {"step": 2, "action": "Parse query intent", "result": f"Query type detected"},
        {"step": 3, "action": "Generate structured response", "result": "Response formulated"},
    ]
    return answer, trace, ["data_fetch", "query_parser", "response_generator"]


@router.post("/query", summary="Natural language environmental query")
async def agent_query(request: AgentQueryRequest, db: AsyncSession = Depends(get_db)):
    """
    Process natural language queries about environmental conditions using AI agent.
    
    Uses LangGraph ReAct agent if available, falls back to rule-based responses.
    """
    start_time = time.time()
    session_id = request.session_id or str(uuid.uuid4())

    # Gather current context
    from app.services.data_fetcher import fetch_weather, fetch_air_quality, fetch_traffic
    from app.config import settings as cfg

    async def safe_fetch(coro, fallback):
        try:
            return await coro
        except Exception as e:
            logger.warning(f"Fetch failed: {e}")
            return fallback

    weather = await safe_fetch(fetch_weather(cfg.default_lat, cfg.default_lon), {})
    aq = await safe_fetch(fetch_air_quality(cfg.default_lat, cfg.default_lon), {})
    
    from app.services.aqi_calculator import compute_aqi as calc_aqi
    try:
        aqi_val, aqi_cat, dominant = calc_aqi(**{k: v for k, v in aq.items() if k in ["pm25","pm10","no2","o3","co","so2"]})
    except Exception as e:
        logger.warning(f"AQI calculation failed: {e}")
        aqi_val, aqi_cat, dominant = 0, "Unknown", "None"
        
    try:
        comp = compliance_checker.assess_compliance(aq)
    except Exception as e:
        logger.warning(f"Compliance assessment failed: {e}")
        comp = {}

    context = {
        "city": cfg.default_city,
        "aqi": aqi_val,
        "aqi_category": aqi_cat,
        "dominant_pollutant": dominant,
        "compliance": comp,
        "session_id": session_id,
        **weather,
    }

    response_text, trace, tools_used = await _best_llm_response(request.query, context)
    latency_ms = round((time.time() - start_time) * 1000, 2)

    # Log to DB
    log = AgentLog(
        session_id=session_id,
        user_query=request.query,
        agent_response=response_text,
        reasoning_trace=trace,
        tools_used=tools_used,
        llm_model=settings.llm_model,
        latency_ms=latency_ms,
        success=True,
    )
    db.add(log)
    await db.commit()

    return {
        "session_id": session_id,
        "query": request.query,
        "response": response_text,
        "reasoning_trace": trace,
        "tools_used": tools_used,
        "latency_ms": latency_ms,
        "model": settings.llm_model,
        "agent_type": "langgraph" if LANGGRAPH_AVAILABLE and get_agent() else "rule_based",
    }


@router.post("/analyze-cause", summary="Root cause analysis of pollution event")
async def analyze_root_cause(
    pollutant: str = Query("pm25", description="Pollutant experiencing elevated levels"),
    location_id: int = Query(1),
    db: AsyncSession = Depends(get_db),
):
    """
    Perform root cause analysis for elevated pollution levels.
    
    Uses causal inference and domain knowledge to identify likely causes.
    """
    start_time = time.time()
    
    # Fetch recent readings
    from_dt = datetime.utcnow() - timedelta(hours=24)
    result = await db.execute(
        select(SensorReading)
        .where(SensorReading.location_id == location_id, SensorReading.timestamp >= from_dt)
        .order_by(desc(SensorReading.timestamp))
        .limit(24)
    )
    readings = result.scalars().all()
    
    if not readings:
        raise HTTPException(status_code=404, detail="No recent readings found")
    
    # Prepare readings data
    readings_data = []
    for r in readings:
        readings_data.append({
            "timestamp": r.timestamp,
            "pm25": r.pm25,
            "pm10": r.pm10,
            "no2": r.no2,
            "o3": r.o3,
            "co": r.co,
            "so2": r.so2,
            "temperature": r.temperature,
            "humidity": r.humidity,
            "wind_speed": r.wind_speed,
            "wind_direction": r.wind_direction,
            "traffic_density_index": r.traffic_density_index,
        })
    
    # Get current value
    current_value = getattr(readings[0], pollutant) or 0
    
    causal_analyzer = get_causal_analyzer()
    
    if causal_analyzer:
        try:
            from datetime import timedelta
            import pandas as pd
            
            # Convert to DataFrame
            df = pd.DataFrame(readings_data)
            
            # Analyze root causes
            analysis = causal_analyzer.analyze_root_cause(
                pollutant=pollutant,
                current_value=current_value,
                historical_data=df,
            )
            
            latency_ms = round((time.time() - start_time) * 1000, 2)
            
            return {
                "pollutant": pollutant,
                "current_value": current_value,
                "location_id": location_id,
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "potential_causes": analysis.get("causes", []),
                "confidence_scores": analysis.get("confidence_scores", {}),
                "recommendations": analysis.get("recommendations", []),
                "explanation": analysis.get("explanation", ""),
                "latency_ms": latency_ms,
            }
            
        except Exception as e:
            logger.error(f"Causal analysis failed: {e}")
    
    # Fallback simple analysis
    from datetime import timedelta
    
    causes = []
    
    # Check wind conditions
    if readings[0].wind_speed and readings[0].wind_speed < 3:
        causes.append({
            "factor": "Low wind speed",
            "contribution": 0.25,
            "explanation": "Stagnant air conditions prevent pollutant dispersion"
        })
    
    # Check traffic
    if readings[0].traffic_density_index and readings[0].traffic_density_index > 0.7:
        causes.append({
            "factor": "High traffic density",
            "contribution": 0.35,
            "explanation": "Vehicle emissions are major PM2.5 and NO2 source"
        })
    
    # Check temperature inversion potential
    if readings[0].temperature and readings[0].humidity:
        if readings[0].temperature < 15 and readings[0].humidity > 80:
            causes.append({
                "factor": "Temperature inversion likely",
                "contribution": 0.30,
                "explanation": "Cold, humid conditions trap pollutants near surface"
            })
    
    latency_ms = round((time.time() - start_time) * 1000, 2)
    
    return {
        "pollutant": pollutant,
        "current_value": current_value,
        "location_id": location_id,
        "analysis_timestamp": datetime.utcnow().isoformat(),
        "potential_causes": causes,
        "analysis_method": "rule_based",
        "latency_ms": latency_ms,
    }


@router.get("/sessions/{session_id}/history", summary="Get conversation history")
async def get_session_history(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get conversation history for a session."""
    result = await db.execute(
        select(AgentLog)
        .where(AgentLog.session_id == session_id)
        .order_by(AgentLog.created_at)
    )
    logs = result.scalars().all()
    
    return {
        "session_id": session_id,
        "messages": [
            {
                "query": log.user_query,
                "response": log.agent_response,
                "timestamp": log.created_at.isoformat() if log.created_at else None,
                "tools_used": log.tools_used,
            }
            for log in logs
        ],
        "total_messages": len(logs),
    }


@router.get("/status", summary="Get agent system status")
async def get_agent_status():
    """Get status of the AI agent subsystem."""
    agent = get_agent()
    
    return {
        "langgraph_available": LANGGRAPH_AVAILABLE,
        "agent_initialized": agent is not None,
        "llm_configured": bool(settings.llm_api_key and not settings.llm_api_key.startswith("your_")),
        "llm_model": settings.llm_model,
        "causal_analyzer_available": get_causal_analyzer() is not None,
        "capabilities": [
            "natural_language_queries",
            "environmental_analysis",
            "health_risk_assessment",
            "regulatory_compliance_check",
            "root_cause_analysis",
            "forecast_interpretation",
        ],
    }
