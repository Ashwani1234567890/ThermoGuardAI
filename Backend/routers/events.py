from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.event import EventCreate, EventResponse, EventAcknowledgeRequest
from backend.services.event_service import EventService

router = APIRouter(prefix="/api/events", tags=["Thermal Events"])


@router.get("", response_model=List[EventResponse], summary="List and Filter Thermal Events")
def list_events(
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type (e.g. hotspot, gradual_heating)"),
    severity: Optional[str] = Query(None, description="Filter by severity: NORMAL, WARNING, CRITICAL, FAULT"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgement state"),
    start_time: Optional[datetime] = Query(None, description="Start date/time"),
    end_time: Optional[datetime] = Query(None, description="End date/time"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Retrieves paginated list of thermal alarms, faults, and threat detection events."""
    return EventService.get_events(
        db=db,
        device_id=device_id,
        event_type=event_type,
        severity=severity,
        acknowledged=acknowledged,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED, summary="Create Manual or External Thermal Event")
def create_event(event_in: EventCreate, db: Session = Depends(get_db)):
    """Allows manual alarm entry or alerts dispatched by external edge monitors."""
    return EventService.create_event(db, event_in)


@router.get("/{event_id}", response_model=EventResponse, summary="Get Specific Event by ID")
def get_event(event_id: int, db: Session = Depends(get_db)):
    """Fetches details of a single thermal event."""
    event = EventService.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found"
        )
    return event


@router.patch("/{event_id}/acknowledge", response_model=EventResponse, summary="Acknowledge Active Event")
def acknowledge_event(
    event_id: int,
    request: EventAcknowledgeRequest,
    db: Session = Depends(get_db)
):
    """Marks an active thermal alarm as acknowledged by an operator or engineer."""
    event = EventService.acknowledge_event(
        db=db,
        event_id=event_id,
        acknowledged_by=request.acknowledged_by
    )
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found"
        )
    return event
