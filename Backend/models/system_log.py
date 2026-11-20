from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.database import Base


class SystemLog(Base):
    """
    Stores system operational, diagnostics, and communication logs.
    """
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(64), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=True, index=True)
    log_level = Column(String(32), default="INFO", nullable=False, index=True)  # INFO, WARNING, ERROR, CRITICAL
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    device = relationship("Device", back_populates="logs")

    __table_args__ = (
        Index("ix_logs_device_time", "device_id", "timestamp"),
        Index("ix_logs_level_time", "log_level", "timestamp"),
    )

    def __repr__(self):
        return f"<SystemLog(level='{self.log_level}', time='{self.timestamp}')>"
