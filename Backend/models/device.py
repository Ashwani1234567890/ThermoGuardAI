from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.orm import relationship
from backend.database import Base


class Device(Base):
    """
    Represents an edge thermal detection unit (e.g. ESP32).
    Designed to support one or multiple devices across a facility.
    """
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(64), unique=True, index=True, nullable=False)
    device_name = Column(String(128), nullable=False)
    status = Column(String(32), default="offline", nullable=False)  # online, offline, warning, critical
    firmware_version = Column(String(32), nullable=True, default="1.0.0")
    ip_address = Column(String(64), nullable=True)
    boot_count = Column(Integer, default=0, nullable=False)
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    readings = relationship("SensorReading", back_populates="device", cascade="all, delete-orphan")
    events = relationship("ThermalEvent", back_populates="device", cascade="all, delete-orphan")
    logs = relationship("SystemLog", back_populates="device", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Device(device_id='{self.device_id}', status='{self.status}', last_seen='{self.last_seen}')>"
