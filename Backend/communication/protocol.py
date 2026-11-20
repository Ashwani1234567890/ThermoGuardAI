import struct
import zlib
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timezone

from backend.schemas.telemetry import (
    TelemetryPayload,
    SensorReadingIn,
    AIPredictionData
)

# Magic bytes identifying ThermoGuardAI binary frames: "TH"
MAGIC_BYTES = b"\x54\x48"
PROTOCOL_VERSION = 1

# Header: Magic(2) + Version(1) + Reserved(1) + DeviceID(16) + SeqNum(4) + BootCount(4) + UptimeMs(4) + SafetyState(1) + AIClass(1) + AIConf(4)
# Header Size: 2 + 1 + 1 + 16 + 4 + 4 + 4 + 1 + 1 + 4 = 38 bytes
HEADER_FORMAT = ">2sBB16sIIIbBf"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# Per sensor: Temp(float 4) + RawADC(uint16 2) + Status(uint8 1) + Reserved(uint8 1) = 8 bytes
SENSOR_FORMAT = ">fHBB"
SENSOR_SIZE = struct.calcsize(SENSOR_FORMAT)
TOTAL_SENSORS = 16

# CRC32 trailer: uint32 (4 bytes)
TRAILER_FORMAT = ">I"
TRAILER_SIZE = struct.calcsize(TRAILER_FORMAT)

PACKET_SIZE = HEADER_SIZE + (SENSOR_SIZE * TOTAL_SENSORS) + TRAILER_SIZE

SAFETY_STATES_REV = {0: "NORMAL", 1: "WARNING", 2: "CRITICAL", 3: "FAULT"}
SAFETY_STATES = {"NORMAL": 0, "WARNING": 1, "CRITICAL": 2, "FAULT": 3}

AI_CLASSES_REV = {
    0: "gradual_heating",
    1: "hotspot",
    2: "normal",
    3: "rapid_rise",
    4: "sensor_anomaly",
    255: None
}
AI_CLASSES = {
    "gradual_heating": 0,
    "hotspot": 1,
    "normal": 2,
    "rapid_rise": 3,
    "sensor_anomaly": 4
}

SENSOR_STATUS_REV = {
    0: "valid",
    1: "open_circuit",
    2: "short_circuit",
    3: "noisy",
    4: "stuck"
}
SENSOR_STATUS = {
    "valid": 0,
    "open_circuit": 1,
    "short_circuit": 2,
    "noisy": 3,
    "stuck": 4
}


class ProtocolError(Exception):
    """Base exception for telemetry protocol validation failures."""
    pass


class InvalidMagicError(ProtocolError):
    pass


class InvalidPacketLengthError(ProtocolError):
    pass


class ChecksumError(ProtocolError):
    pass


@dataclass
class TelemetryPacket:
    device_id: str
    sequence_number: int
    boot_count: int
    uptime_ms: int
    deterministic_safety_state: str
    ai_class: Optional[str]
    ai_confidence: Optional[float]
    temperatures: List[float]
    raw_adcs: List[int]
    statuses: List[str]
    crc32: int

    def to_payload(self) -> TelemetryPayload:
        """Converts binary packet into standard Pydantic TelemetryPayload."""
        readings = [
            SensorReadingIn(
                sensor_id=i,
                temperature=round(self.temperatures[i], 2),
                raw_adc_value=self.raw_adcs[i],
                sensor_status=self.statuses[i]
            )
            for i in range(TOTAL_SENSORS)
        ]

        ai_pred = None
        if self.ai_class:
            ai_pred = AIPredictionData(
                class_index=AI_CLASSES.get(self.ai_class),
                class_name=self.ai_class,
                confidence=round(self.ai_confidence, 4) if self.ai_confidence is not None else None
            )

        return TelemetryPayload(
            device_id=self.device_id,
            timestamp=datetime.now(timezone.utc),
            readings=readings,
            sequence_number=self.sequence_number,
            boot_count=self.boot_count,
            uptime_ms=self.uptime_ms,
            deterministic_safety_state=self.deterministic_safety_state,
            ai_prediction=ai_pred,
            is_simulated=False
        )


def pack_telemetry(
    device_id: str,
    sequence_number: int,
    boot_count: int,
    uptime_ms: int,
    deterministic_safety_state: str,
    ai_class: Optional[str],
    ai_confidence: Optional[float],
    temperatures: List[float],
    raw_adcs: Optional[List[int]] = None,
    statuses: Optional[List[str]] = None
) -> bytes:
    """Encodes a 16-channel telemetry packet into binary format with CRC32."""
    if len(temperatures) != TOTAL_SENSORS:
        raise ValueError(f"Expected {TOTAL_SENSORS} temperatures, got {len(temperatures)}")

    raw_adcs = raw_adcs or [int((t / 100.0) * 4095) for t in temperatures]
    statuses = statuses or ["valid"] * TOTAL_SENSORS

    device_id_bytes = device_id.encode("utf-8")[:16].ljust(16, b"\x00")
    safety_code = SAFETY_STATES.get(deterministic_safety_state.upper(), 0)
    ai_code = AI_CLASSES.get(ai_class, 255) if ai_class else 255
    ai_conf = float(ai_confidence or 0.0)

    header = struct.pack(
        HEADER_FORMAT,
        MAGIC_BYTES,
        PROTOCOL_VERSION,
        0,  # Reserved
        device_id_bytes,
        sequence_number,
        boot_count,
        uptime_ms,
        safety_code,
        ai_code,
        ai_conf
    )

    sensor_bytes = bytearray()
    for i in range(TOTAL_SENSORS):
        s_code = SENSOR_STATUS.get(statuses[i], 0)
        sensor_bytes.extend(
            struct.pack(
                SENSOR_FORMAT,
                float(temperatures[i]),
                int(raw_adcs[i]),
                s_code,
                0  # Reserved
            )
        )

    data_to_checksum = header + sensor_bytes
    crc = zlib.crc32(data_to_checksum) & 0xFFFFFFFF
    trailer = struct.pack(TRAILER_FORMAT, crc)

    return data_to_checksum + trailer


def unpack_telemetry(data: bytes) -> TelemetryPacket:
    """Decodes and rigorously validates binary telemetry data."""
    if len(data) != PACKET_SIZE:
        raise InvalidPacketLengthError(
            f"Invalid packet size: expected {PACKET_SIZE} bytes, received {len(data)} bytes"
        )

    # Validate Magic Bytes
    if data[:2] != MAGIC_BYTES:
        raise InvalidMagicError(
            f"Invalid magic bytes: expected {MAGIC_BYTES.hex()}, got {data[:2].hex()}"
        )

    # Validate CRC32 Checksum
    expected_crc = struct.unpack(TRAILER_FORMAT, data[-4:])[0]
    computed_crc = zlib.crc32(data[:-4]) & 0xFFFFFFFF
    if expected_crc != computed_crc:
        raise ChecksumError(
            f"CRC32 mismatch: expected 0x{expected_crc:08X}, computed 0x{computed_crc:08X}"
        )

    # Unpack Header
    (
        magic,
        version,
        reserved,
        dev_bytes,
        seq_num,
        boot_count,
        uptime_ms,
        safety_code,
        ai_code,
        ai_conf
    ) = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])

    device_id = dev_bytes.decode("utf-8", errors="replace").rstrip("\x00")
    safety_state = SAFETY_STATES_REV.get(safety_code, "NORMAL")
    ai_class = AI_CLASSES_REV.get(ai_code, None)

    # Unpack Sensors
    temperatures = []
    raw_adcs = []
    statuses = []

    offset = HEADER_SIZE
    for i in range(TOTAL_SENSORS):
        temp, adc, s_code, _ = struct.unpack(SENSOR_FORMAT, data[offset:offset + SENSOR_SIZE])
        temperatures.append(temp)
        raw_adcs.append(adc)
        statuses.append(SENSOR_STATUS_REV.get(s_code, "valid"))
        offset += SENSOR_SIZE

    return TelemetryPacket(
        device_id=device_id,
        sequence_number=seq_num,
        boot_count=boot_count,
        uptime_ms=uptime_ms,
        deterministic_safety_state=safety_state,
        ai_class=ai_class,
        ai_confidence=ai_conf if ai_class else None,
        temperatures=temperatures,
        raw_adcs=raw_adcs,
        statuses=statuses,
        crc32=expected_crc
    )


class PacketTracker:
    """
    Maintains sequence numbers and reboot detection per device to catch:
    - Reboots (boot_count increase)
    - Duplicate packets (sequence_number <= last_sequence_number)
    - Dropped/gap sequence numbers (sequence_number > last_sequence_number + 1)
    - Out of order arrivals
    """
    def __init__(self):
        # device_id -> (last_boot_count, last_sequence_number)
        self._devices: Dict[str, Tuple[int, int]] = {}

    def process_packet(self, device_id: str, boot_count: int, sequence_number: int) -> Dict[str, bool]:
        result = {
            "is_reboot": False,
            "is_duplicate": False,
            "is_gap": False,
            "gap_count": 0,
        }

        if device_id not in self._devices:
            self._devices[device_id] = (boot_count, sequence_number)
            return result

        last_boot, last_seq = self._devices[device_id]

        if boot_count > last_boot:
            result["is_reboot"] = True
            self._devices[device_id] = (boot_count, sequence_number)
            return result

        if boot_count == last_boot:
            if sequence_number <= last_seq:
                result["is_duplicate"] = True
                return result
            if sequence_number > last_seq + 1:
                result["is_gap"] = True
                result["gap_count"] = sequence_number - (last_seq + 1)

            self._devices[device_id] = (boot_count, sequence_number)

        return result
