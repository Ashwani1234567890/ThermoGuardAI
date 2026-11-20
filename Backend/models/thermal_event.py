from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.database import Base


class ThermalEvent(Base):
    """
    Represents detected thermal threats, alarms, or hardware faults.
    Maintains strict separation between deterministic safety logic (severity)
    and AI inference (ai_class, confidence, probabilities).
    """
    __tablename__ = "thermal_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(64), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)  # hotspot, gradual_heating, rapid_rise, sensor_fault, etc.
    severity = Column(String(32), nullable=False, index=True)  # NORMAL, WARNING, CRITICAL, FAULT
    affected_sensor = Column(Integer, nullable=True)  # 0-15 or None if widespread
    temperature = Column(Float, nullable=False)  # Peak or trigger temperature
    temperature_rise_rate = Column(Float, nullable=True)  # Rate of change (°C/s or per window)
    
    # Separated AI inference fields
    confidence = Column(Float, nullable=True)  # Extra Trees confidence (0.0 to 1.0)
    ai_class = Column(String(64), nullable=True)  # Extra Trees predicted class name
    
    description = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    acknowledged = Column(Boolean, default=False, nullable=False, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(128), nullable=True)

    # Relationships
    device = relationship("Device", back_populates="events")

    __table_args__ = (
        Index("ix_events_device_severity", "device_id", "severity"),
        Index("ix_events_timestamp_ack", "timestamp", "acknowledged"),
    )

    def __repr__(self):
        return f"<ThermalEvent(id={self.id}, device='{self.device_id}', type='{self.event_type}', severity='{self.severity}')>"
