"""
Router: WebSocket — Real-time live data streaming
"""

import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

from app.services.cache_service import get_redis
from app.services import data_fetcher, aqi_calculator

router = APIRouter()
logger = structlog.get_logger(__name__)

connected_clients: set[WebSocket] = set()


@router.websocket("/live")
async def websocket_live(websocket: WebSocket):
    """WebSocket endpoint broadcasting live environmental data every 30 seconds."""
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info(f"WebSocket client connected. Total: {len(connected_clients)}")

    try:
        # Subscribe to Redis pub/sub for real-time events
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe("greenpulse:live")

        # Send initial ping
        await websocket.send_json({"type": "connected", "message": "GreenPulse AI live stream active", "timestamp": datetime.utcnow().isoformat()})

        async def listen_redis():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await websocket.send_json({"type": "update", "data": data, "timestamp": datetime.utcnow().isoformat()})
                    except Exception as e:
                        logger.warning(f"WS send error: {e}")
                        break

        async def ping_loop():
            """Heartbeat ping every 25 seconds."""
            while True:
                await asyncio.sleep(25)
                try:
                    await websocket.send_json({"type": "ping", "timestamp": datetime.utcnow().isoformat()})
                except Exception:
                    break

        # Run both concurrently
        await asyncio.gather(listen_redis(), ping_loop(), return_exceptions=True)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connected_clients.discard(websocket)


async def broadcast(message: dict):
    """Broadcast a message to all connected WebSocket clients."""
    dead = set()
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            dead.add(client)
    connected_clients -= dead
