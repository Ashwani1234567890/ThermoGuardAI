from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.telemetry import (
    TelemetryPayload,
    TelemetryBatchPayload,
    TelemetryResponse,
    GridTelemetryResponse,
    HistoricalTelemetryResponse,
)
from backend.services.telemetry_service import TelemetryService

router = APIRouter(prefix="/api/telemetry", tags=["Telemetry"])


@router.post("", response_model=TelemetryResponse, status_code=status.HTTP_201_CREATED, summary="Ingest Single Telemetry Cycle")
def ingest_telemetry(payload: TelemetryPayload, db: Session = Depends(get_db)):
    """
    Ingests one complete acquisition cycle covering all 16 sensors.
    Validates sensor values, calculates spatial metrics, updates device status,
    and records safety events if thresholds are exceeded.
    """
    try:
        return TelemetryService.save_telemetry(db, payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to ingest telemetry: {str(e)}"
        )


@router.post("/batch", response_model=List[TelemetryResponse], status_code=status.HTTP_201_CREATED, summary="Ingest Telemetry Batch")
def ingest_telemetry_batch(payload: TelemetryBatchPayload, db: Session = Depends(get_db)):
    """Ingests multiple acquisition cycles in a single batch request."""
    try:
        return TelemetryService.save_telemetry_batch(db, payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch ingestion failed: {str(e)}"
        )


@router.get("/latest/{device_id}", response_model=GridTelemetryResponse, summary="Get Latest 4x4 Grid Telemetry")
def get_latest_telemetry(device_id: str, db: Session = Depends(get_db)):
    """
    Returns the most recent complete 16-channel acquisition cycle
    formatted as a 4x4 matrix ready for dashboard heatmaps and visualization.
    """
    data = TelemetryService.get_latest_telemetry(db, device_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No telemetry records found for device '{device_id}'"
        )
    return data


@router.get("/history/{device_id}", response_model=HistoricalTelemetryResponse, summary="Query Historical Telemetry")
def get_telemetry_history(
    device_id: str,
    sensor_id: Optional[int] = Query(None, ge=0, le=15, description="Filter for specific sensor ID 0-15"),
    start_time: Optional[datetime] = Query(None, description="ISO format start datetime"),
    end_time: Optional[datetime] = Query(None, description="ISO format end datetime"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Items per page"),
    db: Session = Depends(get_db),
):
    """
    Retrieves time-series temperature history for a device with optional
    sensor-specific filtering and pagination.
    """
    return TelemetryService.get_telemetry_history(
        db=db,
        device_id=device_id,
        sensor_id=sensor_id,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )
