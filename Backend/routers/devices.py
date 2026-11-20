from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.device import DeviceRegisterRequest, DeviceResponse, DeviceStatusResponse
from backend.services.device_service import DeviceService

router = APIRouter(prefix="/api/devices", tags=["Devices"])


@router.get("", response_model=List[DeviceResponse], summary="List All Registered Edge Devices")
def list_devices(db: Session = Depends(get_db)):
    """Returns all registered ESP32 edge devices."""
    return DeviceService.get_all_devices(db)


@router.post("/register", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED, summary="Register or Update Device")
def register_device(request: DeviceRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new edge sensor device or updates existing metadata."""
    return DeviceService.register_device(db, request)


@router.get("/{device_id}", response_model=DeviceResponse, summary="Get Device Details by ID")
def get_device(device_id: str, db: Session = Depends(get_db)):
    """Fetches details for a specific edge device."""
    device = DeviceService.get_device(db, device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with ID '{device_id}' not found"
        )
    return device


@router.get("/{device_id}/status", response_model=DeviceStatusResponse, summary="Check Real-Time Device Status")
def get_device_status(device_id: str, db: Session = Depends(get_db)):
    """Returns live online/offline state based on last seen telemetry."""
    status_info = DeviceService.get_device_status(db, device_id)
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with ID '{device_id}' not found"
        )
    return status_info
