import uuid
import numpy as np
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.models.device import Device
from backend.models.sensor_reading import SensorReading
from backend.models.thermal_event import ThermalEvent
from backend.schemas.telemetry import (
    TelemetryPayload,
    TelemetryBatchPayload,
    TelemetryResponse,
    TelemetrySummary,
    GridTelemetryResponse,
    HistoricalTelemetryResponse,
    HistoricalReadingItem,
)
from backend.services.device_service import DeviceService
from backend.config import settings


class TelemetryService:
    @staticmethod
    def calculate_summary(readings: List[float]) -> TelemetrySummary:
        """Computes spatial thermal metrics matching edge feature extraction."""
        temps = np.array(readings, dtype=float)
        mean_t = float(np.mean(temps))
        max_t = float(np.max(temps))
        min_t = float(np.min(temps))
        spatial_range = float(max_t - min_t)
        spatial_std = float(np.std(temps))
        hottest_sensor = int(np.argmax(temps))
        coldest_sensor = int(np.argmin(temps))

        return TelemetrySummary(
            mean_temperature=round(mean_t, 2),
            max_temperature=round(max_t, 2),
            min_temperature=round(min_t, 2),
            spatial_range=round(spatial_range, 2),
            spatial_std=round(spatial_std, 2),
            hottest_sensor_id=hottest_sensor,
            coldest_sensor_id=coldest_sensor,
        )

    @classmethod
    def save_telemetry(cls, db: Session, payload: TelemetryPayload) -> TelemetryResponse:
        # Update device heartbeat and boot count
        DeviceService.update_last_seen(
            db=db,
            device_id=payload.device_id,
            boot_count=payload.boot_count,
            status="online"
        )

        batch_id = str(uuid.uuid4())
        record_time = payload.timestamp or datetime.now(timezone.utc)
        if record_time.tzinfo is None:
            record_time = record_time.replace(tzinfo=timezone.utc)

        temp_list = []
        db_records = []

        for r in payload.readings:
            temp_list.append(r.temperature)
            db_records.append(
                SensorReading(
                    device_id=payload.device_id,
                    batch_id=batch_id,
                    timestamp=record_time,
                    sensor_id=r.sensor_id,
                    temperature=round(r.temperature, 2),
                    raw_adc_value=r.raw_adc_value,
                    sensor_status=r.sensor_status,
                )
            )

        db.bulk_save_objects(db_records)

        # Calculate spatial statistics
        summary = cls.calculate_summary(temp_list)

        # Deterministic Safety Checks (Independent of AI inference)
        safety_state = payload.deterministic_safety_state.upper()
        ai_class = payload.ai_prediction.class_name if payload.ai_prediction else None
        ai_conf = payload.ai_prediction.confidence if payload.ai_prediction else None

        # Automatic Event Generation if safety thresholds are breached
        if summary.max_temperature >= settings.MAX_ALLOWABLE_TEMPERATURE_C:
            safety_state = "CRITICAL"
            event = ThermalEvent(
                device_id=payload.device_id,
                event_type="high_temperature_threshold",
                severity="CRITICAL",
                affected_sensor=summary.hottest_sensor_id,
                temperature=summary.max_temperature,
                temperature_rise_rate=None,
                confidence=ai_conf,
                ai_class=ai_class,
                description=f"Critical temperature threshold breached: {summary.max_temperature}°C on sensor {summary.hottest_sensor_id} (Limit: {settings.MAX_ALLOWABLE_TEMPERATURE_C}°C)",
                timestamp=record_time,
            )
            db.add(event)
        elif summary.max_temperature >= settings.WARNING_TEMPERATURE_C:
            if safety_state == "NORMAL":
                safety_state = "WARNING"
            event = ThermalEvent(
                device_id=payload.device_id,
                event_type="warning_temperature_threshold",
                severity="WARNING",
                affected_sensor=summary.hottest_sensor_id,
                temperature=summary.max_temperature,
                temperature_rise_rate=None,
                confidence=ai_conf,
                ai_class=ai_class,
                description=f"Warning temperature threshold exceeded: {summary.max_temperature}°C on sensor {summary.hottest_sensor_id} (Limit: {settings.WARNING_TEMPERATURE_C}°C)",
                timestamp=record_time,
            )
            db.add(event)
        elif ai_class and ai_class != "normal" and (ai_conf is not None and ai_conf > 0.60):
            # Record an AI-detected anomaly event while preserving separate confidence and deterministic severity
            event_severity = "WARNING" if ai_class in ["hotspot", "gradual_heating"] else "CRITICAL"
            event = ThermalEvent(
                device_id=payload.device_id,
                event_type=f"ai_{ai_class}",
                severity=event_severity,
                affected_sensor=summary.hottest_sensor_id if ai_class in ["hotspot", "sensor_anomaly"] else None,
                temperature=summary.max_temperature,
                temperature_rise_rate=None,
                confidence=ai_conf,
                ai_class=ai_class,
                description=f"AI model detected {ai_class} with {ai_conf * 100:.1f}% confidence.",
                timestamp=record_time,
            )
            db.add(event)

        db.commit()

        return TelemetryResponse(
            status="success",
            batch_id=batch_id,
            device_id=payload.device_id,
            timestamp=record_time,
            readings_saved=len(db_records),
            summary=summary,
            safety_state=safety_state,
            ai_class=ai_class,
            ai_confidence=ai_conf,
        )

    @classmethod
    def save_telemetry_batch(cls, db: Session, batch_payload: TelemetryBatchPayload) -> List[TelemetryResponse]:
        results = []
        for payload in batch_payload.batches:
            res = cls.save_telemetry(db, payload)
            results.append(res)
        return results

    @classmethod
    def get_latest_telemetry(cls, db: Session, device_id: str) -> Optional[GridTelemetryResponse]:
        # Find latest reading for device
        latest_reading = (
            db.query(SensorReading)
            .filter(SensorReading.device_id == device_id)
            .order_by(desc(SensorReading.timestamp), desc(SensorReading.id))
            .first()
        )
        if not latest_reading:
            return None

        batch_readings = (
            db.query(SensorReading)
            .filter(SensorReading.batch_id == latest_reading.batch_id)
            .order_by(SensorReading.sensor_id.asc())
            .all()
        )

        if len(batch_readings) < 16:
            return None

        temps = [r.temperature for r in batch_readings]
        grid_4x4 = [
            temps[0:4],
            temps[4:8],
            temps[8:12],
            temps[12:16],
        ]

        summary = cls.calculate_summary(temps)

        # Check online status
        device_status = DeviceService.get_device_status(db, device_id)
        is_online = device_status.is_online if device_status else False

        # Get latest event for safety state
        latest_event = (
            db.query(ThermalEvent)
            .filter(ThermalEvent.device_id == device_id)
            .order_by(desc(ThermalEvent.timestamp))
            .first()
        )
        safety_state = "NORMAL"
        ai_class = None
        ai_conf = None
        if latest_event and not latest_event.acknowledged:
            safety_state = latest_event.severity
            ai_class = latest_event.ai_class
            ai_conf = latest_event.confidence

        return GridTelemetryResponse(
            device_id=device_id,
            timestamp=latest_reading.timestamp,
            grid_4x4=grid_4x4,
            summary=summary,
            safety_state=safety_state,
            ai_class=ai_class,
            ai_confidence=ai_conf,
            is_online=is_online,
        )

    @classmethod
    def get_telemetry_history(
        cls,
        db: Session,
        device_id: str,
        sensor_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> HistoricalTelemetryResponse:
        query = db.query(SensorReading).filter(SensorReading.device_id == device_id)

        if sensor_id is not None:
            query = query.filter(SensorReading.sensor_id == sensor_id)
        if start_time:
            query = query.filter(SensorReading.timestamp >= start_time)
        if end_time:
            query = query.filter(SensorReading.timestamp <= end_time)

        total_records = query.count()
        readings = (
            query.order_by(desc(SensorReading.timestamp))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items = [
            HistoricalReadingItem(
                timestamp=r.timestamp,
                sensor_id=r.sensor_id,
                temperature=r.temperature,
                raw_adc_value=r.raw_adc_value,
                sensor_status=r.sensor_status,
            )
            for r in readings
        ]

        return HistoricalTelemetryResponse(
            device_id=device_id,
            total_records=total_records,
            page=page,
            page_size=page_size,
            readings=items,
        )
