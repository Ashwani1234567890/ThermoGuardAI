from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.models.thermal_event import ThermalEvent
from backend.schemas.event import EventCreate


class EventService:
    @staticmethod
    def create_event(db: Session, event_in: EventCreate) -> ThermalEvent:
        event = ThermalEvent(
            device_id=event_in.device_id,
            event_type=event_in.event_type,
            severity=event_in.severity.upper(),
            affected_sensor=event_in.affected_sensor,
            temperature=event_in.temperature,
            temperature_rise_rate=event_in.temperature_rise_rate,
            confidence=event_in.confidence,
            ai_class=event_in.ai_class,
            description=event_in.description,
            timestamp=event_in.timestamp or datetime.now(timezone.utc),
            acknowledged=False
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def get_events(
        db: Session,
        device_id: Optional[str] = None,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> List[ThermalEvent]:
        query = db.query(ThermalEvent)

        if device_id:
            query = query.filter(ThermalEvent.device_id == device_id)
        if event_type:
            query = query.filter(ThermalEvent.event_type == event_type)
        if severity:
            query = query.filter(ThermalEvent.severity == severity.upper())
        if acknowledged is not None:
            query = query.filter(ThermalEvent.acknowledged == acknowledged)
        if start_time:
            query = query.filter(ThermalEvent.timestamp >= start_time)
        if end_time:
            query = query.filter(ThermalEvent.timestamp <= end_time)

        return (
            query.order_by(desc(ThermalEvent.timestamp))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

    @staticmethod
    def get_event_by_id(db: Session, event_id: int) -> Optional[ThermalEvent]:
        return db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()

    @staticmethod
    def acknowledge_event(
        db: Session,
        event_id: int,
        acknowledged_by: str = "operator"
    ) -> Optional[ThermalEvent]:
        event = db.query(ThermalEvent).filter(ThermalEvent.id == event_id).first()
        if not event:
            return None
        
        event.acknowledged = True
        event.acknowledged_at = datetime.now(timezone.utc)
        event.acknowledged_by = acknowledged_by
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def count_active_alarms(db: Session) -> int:
        return db.query(ThermalEvent).filter(ThermalEvent.acknowledged == False).count()
