from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class DeviceRegisterRequest(BaseModel):
    """Schema for registering a new edge sensor device."""
    device_id: str = Field(..., min_length=2, max_length=64, description="Unique identifier for the ESP32 device")
    device_name: str = Field(..., min_length=2, max_length=128, description="Human-readable device name")
    firmware_version: Optional[str] = Field("1.0.0", max_length=32)
    ip_address: Optional[str] = Field(None, max_length=64)


class DeviceResponse(BaseModel):
    """Device details response schema."""
    id: int
    device_id: str
    device_name: str
    status: str
    firmware_version: Optional[str]
    ip_address: Optional[str]
    boot_count: int
    last_seen: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceStatusResponse(BaseModel):
    """Real-time online/offline and health status response."""
    device_id: str
    device_name: str
    status: str  # online, offline, warning, critical
    is_online: bool
    last_seen: datetime
    seconds_since_last_seen: float
    firmware_version: Optional[str]
    boot_count: int
