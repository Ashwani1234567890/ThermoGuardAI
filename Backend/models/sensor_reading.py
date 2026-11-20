from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.database import Base


class SensorReading(Base):
    """
    Stores individual sensor readings.
    For each 16-channel scan cycle, 16 records are persisted sharing the same
    batch_id and timestamp, allowing granular per-sensor querying and spatial aggregations.
    """
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(64), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(String(64), nullable=False, index=True)  # Groups 16 readings in 1 acquisition cycle
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    sensor_id = Column(Integer, nullable=False)  # 0 to 15 (representing 4x4 matrix position)
    temperature = Column(Float, nullable=False)
    raw_adc_value = Column(Integer, nullable=False)
    sensor_status = Column(String(32), default="valid", nullable=False)  # valid, open_circuit, short_circuit, noisy, stuck

    # Relationships
    device = relationship("Device", back_populates="readings")

    # Composite indexes for fast time-series & spatial retrieval
    __table_args__ = (
        Index("ix_readings_device_timestamp", "device_id", "timestamp"),
        Index("ix_readings_device_sensor_time", "device_id", "sensor_id", "timestamp"),
        Index("ix_readings_batch", "batch_id"),
    )

    def __repr__(self):
        return f"<SensorReading(device='{self.device_id}', sensor={self.sensor_id}, temp={self.temperature:.2f}C)>"
