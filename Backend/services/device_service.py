from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.models.device import Device
from backend.schemas.device import DeviceRegisterRequest, DeviceStatusResponse
from backend.config import settings


class DeviceService:
    @staticmethod
    def get_device(db: Session, device_id: str) -> Optional[Device]:
        return db.query(Device).filter(Device.device_id == device_id).first()

    @staticmethod
    def get_all_devices(db: Session) -> List[Device]:
        return db.query(Device).order_by(Device.created_at.desc()).all()

    @staticmethod
    def register_device(db: Session, request: DeviceRegisterRequest) -> Device:
        device = db.query(Device).filter(Device.device_id == request.device_id).first()
        now = datetime.now(timezone.utc)
        if device:
            device.device_name = request.device_name
            if request.firmware_version:
                device.firmware_version = request.firmware_version
            if request.ip_address:
                device.ip_address = request.ip_address
            device.last_seen = now
        else:
            device = Device(
                device_id=request.device_id,
                device_name=request.device_name,
                firmware_version=request.firmware_version or "1.0.0",
                ip_address=request.ip_address,
                status="online",
                last_seen=now,
                created_at=now
            )
            db.add(device)
        db.commit()
        db.refresh(device)
        return device

    @staticmethod
    def update_last_seen(
        db: Session,
        device_id: str,
        ip_address: Optional[str] = None,
        boot_count: Optional[int] = None,
        status: Optional[str] = None
    ) -> Device:
        device = db.query(Device).filter(Device.device_id == device_id).first()
        now = datetime.now(timezone.utc)
        if not device:
            device = Device(
                device_id=device_id,
                device_name=f"Device-{device_id}",
                firmware_version="1.0.0",
                ip_address=ip_address,
                boot_count=boot_count or 0,
                status="online",
                last_seen=now,
                created_at=now
            )
            db.add(device)
        else:
            device.last_seen = now
            if ip_address:
                device.ip_address = ip_address
            if boot_count is not None:
                device.boot_count = boot_count
            if status:
                device.status = status
            elif device.status == "offline":
                device.status = "online"
        db.commit()
        db.refresh(device)
        return device

    @staticmethod
    def get_device_status(db: Session, device_id: str) -> Optional[DeviceStatusResponse]:
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            return None
        
        now = datetime.now(timezone.utc)
        # Ensure device.last_seen is tz-aware for comparison
        last_seen = device.last_seen
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
            
        seconds_diff = (now - last_seen).total_seconds()
        is_online = seconds_diff <= settings.DEVICE_OFFLINE_THRESHOLD_SECONDS

        computed_status = device.status
        if not is_online:
            computed_status = "offline"
        
        return DeviceStatusResponse(
            device_id=device.device_id,
            device_name=device.device_name,
            status=computed_status,
            is_online=is_online,
            last_seen=device.last_seen,
            seconds_since_last_seen=round(seconds_diff, 1),
            firmware_version=device.firmware_version,
            boot_count=device.boot_count
        )
