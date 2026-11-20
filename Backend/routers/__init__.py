from backend.routers.health import router as health_router
from backend.routers.devices import router as devices_router
from backend.routers.telemetry import router as telemetry_router
from backend.routers.events import router as events_router

__all__ = ["health_router", "devices_router", "telemetry_router", "events_router"]
