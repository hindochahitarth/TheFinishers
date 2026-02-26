"""
GreenPulse AI — FastAPI Application Entry Point
"""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.database import create_tables
from app.routers import monitoring, forecasting, alerts, compliance, agents, recommendations, websocket as ws_router

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(level=settings.log_level)
logger = structlog.get_logger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle handler."""
    logger.info("🌿 GreenPulse AI starting up...", env=settings.environment)
    await create_tables()
    logger.info("✅ Database tables verified")
    yield
    logger.info("🛑 GreenPulse AI shutting down...")


# ── App Init ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Research-grade AI environmental intelligence platform. "
        "Real-time AQI monitoring, forecasting, anomaly detection, "
        "causal reasoning, and regulatory compliance."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(monitoring.router,      prefix="/api/v1/monitoring",      tags=["Monitoring"])
app.include_router(forecasting.router,     prefix="/api/v1/forecast",         tags=["Forecasting"])
app.include_router(alerts.router,          prefix="/api/v1/alerts",           tags=["Alerts"])
app.include_router(compliance.router,      prefix="/api/v1/compliance",       tags=["Compliance"])
app.include_router(agents.router,          prefix="/api/v1/agents",           tags=["AI Agents"])
app.include_router(recommendations.router, prefix="/api/v1/recommendations",  tags=["Recommendations"])
app.include_router(ws_router.router,       prefix="/ws",                      tags=["WebSocket"])


# ── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
