from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class EventCreate(BaseModel):
    """Schema for reporting a thermal event or anomaly."""
    device_id: str = Field(..., min_length=2, max_length=64)
    event_type: str = Field(..., description="hotspot, gradual_heating, rapid_rise, sensor_fault, etc.")
    severity: str = Field(..., description="NORMAL, WARNING, CRITICAL, FAULT")
    affected_sensor: Optional[int] = Field(None, ge=0, le=15)
    temperature: float = Field(..., description="Peak or trigger temperature")
    temperature_rise_rate: Optional[float] = Field(None, description="Rate of temperature rise")
    
    # Separated AI inference
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    ai_class: Optional[str] = None
    
    description: str = Field(..., min_length=3)
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class EventResponse(BaseModel):
    """Thermal event response model."""
    id: int
    device_id: str
    event_type: str
    severity: str
    affected_sensor: Optional[int]
    temperature: float
    temperature_rise_rate: Optional[float]
    confidence: Optional[float]
    ai_class: Optional[str]
    description: str
    timestamp: datetime
    acknowledged: bool
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class EventAcknowledgeRequest(BaseModel):
    """Payload for acknowledging an active alert."""
    acknowledged_by: str = Field("operator", min_length=2, max_length=128)
