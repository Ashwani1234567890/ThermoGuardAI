from datetime import datetime, timezone
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class SensorReadingIn(BaseModel):
    """Validation schema for a single sensor's reading within an acquisition cycle."""
    sensor_id: int = Field(..., ge=0, le=15, description="Sensor index in 4x4 grid (0 to 15)")
    temperature: float = Field(..., ge=-50.0, le=250.0, description="Calibrated temperature in °C")
    raw_adc_value: int = Field(..., ge=0, le=4095, description="12-bit raw ADC reading (0-4095)")
    sensor_status: str = Field("valid", description="Status flag: valid, open_circuit, short_circuit, noisy, stuck")


class AIPredictionData(BaseModel):
    """Extra Trees model inference results reported by ESP32."""
    class_index: Optional[int] = Field(None, ge=0, le=4)
    class_name: Optional[str] = Field(None, description="gradual_heating, hotspot, normal, rapid_rise, sensor_anomaly")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    probabilities: Optional[List[float]] = Field(None)


class TelemetryPayload(BaseModel):
    """
    Complete telemetry packet for one acquisition cycle (16 sensors).
    Separates deterministic safety state from AI inference.
    """
    device_id: str = Field(..., min_length=2, max_length=64)
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    readings: List[SensorReadingIn] = Field(..., description="Array of exactly 16 sensor readings")
    sequence_number: Optional[int] = Field(None, ge=0, description="Monotonically increasing packet sequence")
    boot_count: Optional[int] = Field(None, ge=0, description="Device boot/reboot count")
    uptime_ms: Optional[int] = Field(None, ge=0, description="ESP32 uptime in milliseconds")
    
    # Deterministic Safety State
    deterministic_safety_state: str = Field("NORMAL", description="NORMAL, WARNING, CRITICAL, FAULT")
    
    # Separate AI ML Inference (Extra Trees)
    ai_prediction: Optional[AIPredictionData] = None

    # Telemetry simulation flag
    is_simulated: bool = Field(False, description="Flag indicating simulated data")

    @field_validator("readings")
    @classmethod
    def validate_16_sensors(cls, readings: List[SensorReadingIn]) -> List[SensorReadingIn]:
        if len(readings) != 16:
            raise ValueError(f"Telemetry payload must contain exactly 16 sensor readings (got {len(readings)})")
        
        sensor_ids = [r.sensor_id for r in readings]
        if len(set(sensor_ids)) != 16:
            raise ValueError("Telemetry readings must cover unique sensor IDs 0 through 15 without duplicates")
        return sorted(readings, key=lambda x: x.sensor_id)


class TelemetryBatchPayload(BaseModel):
    """Batch ingestion of multiple acquisition cycles."""
    batches: List[TelemetryPayload] = Field(..., min_length=1, max_length=100)


class TelemetrySummary(BaseModel):
    """Calculated thermal spatial metrics for an acquisition cycle."""
    mean_temperature: float
    max_temperature: float
    min_temperature: float
    spatial_range: float
    spatial_std: float
    hottest_sensor_id: int
    coldest_sensor_id: int


class TelemetryResponse(BaseModel):
    """Response after persisting telemetry."""
    status: str = "success"
    batch_id: str
    device_id: str
    timestamp: datetime
    readings_saved: int
    summary: TelemetrySummary
    safety_state: str
    ai_class: Optional[str] = None
    ai_confidence: Optional[float] = None


class GridTelemetryResponse(BaseModel):
    """4x4 temperature matrix view tailored for thermal heatmaps and dashboard display."""
    device_id: str
    timestamp: datetime
    grid_4x4: List[List[float]] = Field(..., description="4x4 grid of temperatures row by row: [[0..3], [4..7], [8..11], [12..15]]")
    summary: TelemetrySummary
    safety_state: str
    ai_class: Optional[str] = None
    ai_confidence: Optional[float] = None
    is_online: bool


class HistoricalReadingItem(BaseModel):
    timestamp: datetime
    sensor_id: int
    temperature: float
    raw_adc_value: int
    sensor_status: str

    model_config = ConfigDict(from_attributes=True)


class HistoricalTelemetryResponse(BaseModel):
    device_id: str
    total_records: int
    page: int
    page_size: int
    readings: List[HistoricalReadingItem]
