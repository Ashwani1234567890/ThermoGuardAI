import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database import get_db
from backend.config import settings
from backend.schemas.health import HealthResponse
from backend.services.device_service import DeviceService
from backend.services.event_service import EventService

router = APIRouter(tags=["Health"])
start_time = time.time()


@router.get("/", summary="Root Health Probe")
def root():
    """Simple root probe verifying service availability."""
    return {
        "status": "online",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "docs_url": "/docs"
    }


@router.get("/api/health", response_model=HealthResponse, summary="Comprehensive System Health Check")
def health_check(db: Session = Depends(get_db)):
    """
    Checks backend connectivity, database status, registered devices,
    and active unacknowledged alarm counts.
    """
    db_connected = False
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False

    device_count = len(DeviceService.get_all_devices(db)) if db_connected else 0
    active_alarms = EventService.count_active_alarms(db) if db_connected else 0

    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        database_connected=db_connected,
        registered_devices=device_count,
        active_alarms=active_alarms,
        system_time=datetime.now(timezone.utc).isoformat()
    )
