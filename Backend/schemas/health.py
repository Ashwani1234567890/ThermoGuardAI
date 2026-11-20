from typing import Dict, Any, Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Backend and database health check schema."""
    status: str = "ok"
    app_name: str
    version: str
    environment: str
    database_connected: bool
    registered_devices: int
    active_alarms: int
    system_time: str
