import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.database import init_db
from backend.routers import (
    health_router,
    devices_router,
    telemetry_router,
    events_router,
)
from backend.communication.udp_receiver import start_udp_receiver

# Configure structured logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("thermoguard.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application lifecycle:
    1. Initializes SQLite tables on startup.
    2. Spawns asynchronous UDP telemetry receiver if enabled.
    3. Handles graceful cleanup on shutdown.
    """
    logger.info("Initializing ThermoGuardAI Database Schema...")
    init_db()
    logger.info("Database initialized successfully.")

    udp_transport = None
    if settings.UDP_ENABLED:
        try:
            logger.info(f"Starting UDP Telemetry Receiver on {settings.UDP_HOST}:{settings.UDP_PORT}...")
            udp_transport, _ = await start_udp_receiver(
                host=settings.UDP_HOST,
                port=settings.UDP_PORT
            )
            logger.info("UDP Telemetry Receiver started successfully.")
        except Exception as e:
            logger.warning(f"Could not bind UDP receiver: {e}. Falling back to REST-only ingestion.")

    yield

    # Graceful shutdown
    if udp_transport:
        logger.info("Closing UDP Telemetry transport...")
        udp_transport.close()
    logger.info("ThermoGuardAI backend shutdown complete.")


# Initialize FastAPI Application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Decentralized Thermal Threat Detection at the Edge – Ingestion & Monitoring API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(health_router)
app.include_router(devices_router)
app.include_router(telemetry_router)
app.include_router(events_router)


# Real-time WebSocket connection manager for thermal dashboard clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        if device_id not in self.active_connections:
            self.active_connections[device_id] = []
        self.active_connections[device_id].append(websocket)

    def disconnect(self, device_id: str, websocket: WebSocket):
        if device_id in self.active_connections:
            if websocket in self.active_connections[device_id]:
                self.active_connections[device_id].remove(websocket)

    async def broadcast(self, device_id: str, message: dict):
        if device_id in self.active_connections:
            for connection in self.active_connections[device_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass


manager = ConnectionManager()


@app.websocket("/ws/telemetry/{device_id}")
async def websocket_telemetry(websocket: WebSocket, device_id: str):
    """
    WebSocket endpoint streaming live 4x4 thermal grid telemetry
    to connected dashboard clients.
    """
    await manager.connect(device_id, websocket)
    try:
        while True:
            # Keep connection alive; clients can send ping
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(device_id, websocket)
    except Exception:
        manager.disconnect(device_id, websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
