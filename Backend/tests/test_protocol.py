import pytest
from backend.communication.protocol import (
    pack_telemetry,
    unpack_telemetry,
    PacketTracker,
    ChecksumError,
    InvalidMagicError,
    InvalidPacketLengthError,
)


def test_pack_and_unpack_telemetry():
    device_id = "ESP32-UNIT-A"
    seq = 101
    boot = 3
    uptime = 45000
    temps = [24.0 + (i * 0.5) for i in range(16)]

    packed = pack_telemetry(
        device_id=device_id,
        sequence_number=seq,
        boot_count=boot,
        uptime_ms=uptime,
        deterministic_safety_state="WARNING",
        ai_class="hotspot",
        ai_confidence=0.912,
        temperatures=temps
    )

    unpacked = unpack_telemetry(packed)
    assert unpacked.device_id == device_id
    assert unpacked.sequence_number == seq
    assert unpacked.boot_count == boot
    assert unpacked.uptime_ms == uptime
    assert unpacked.deterministic_safety_state == "WARNING"
    assert unpacked.ai_class == "hotspot"
    assert abs(unpacked.ai_confidence - 0.912) < 0.001
    assert len(unpacked.temperatures) == 16
    assert abs(unpacked.temperatures[0] - 24.0) < 0.01


def test_corrupt_packet_checksum_rejection():
    temps = [25.0] * 16
    packed = pack_telemetry("ESP32-CRC", 1, 0, 1000, "NORMAL", "normal", 0.95, temps)

    # Corrupt a single byte in the payload
    corrupted = bytearray(packed)
    corrupted[20] ^= 0x55

    with pytest.raises(ChecksumError):
        unpack_telemetry(bytes(corrupted))


def test_invalid_magic_bytes():
    temps = [25.0] * 16
    packed = pack_telemetry("ESP32-MAGIC", 1, 0, 1000, "NORMAL", "normal", 0.95, temps)

    # Modify magic bytes from 'TH' to 'XX'
    corrupted = bytearray(packed)
    corrupted[0] = ord("X")
    corrupted[1] = ord("X")

    with pytest.raises(InvalidMagicError):
        unpack_telemetry(bytes(corrupted))


def test_invalid_packet_length():
    with pytest.raises(InvalidPacketLengthError):
        unpack_telemetry(b"\x54\x48\x01\x00")


def test_packet_tracker_reboot_and_duplicate():
    tracker = PacketTracker()
    dev = "ESP32-TRK-01"

    # Initial packet
    res1 = tracker.process_packet(dev, boot_count=1, sequence_number=10)
    assert res1["is_reboot"] is False
    assert res1["is_duplicate"] is False

    # Sequential packet
    res2 = tracker.process_packet(dev, boot_count=1, sequence_number=11)
    assert res2["is_duplicate"] is False

    # Duplicate / out of order packet
    res_dup = tracker.process_packet(dev, boot_count=1, sequence_number=10)
    assert res_dup["is_duplicate"] is True

    # Packet gap
    res_gap = tracker.process_packet(dev, boot_count=1, sequence_number=15)
    assert res_gap["is_gap"] is True
    assert res_gap["gap_count"] == 3

    # ESP32 Reboot detected
    res_reboot = tracker.process_packet(dev, boot_count=2, sequence_number=1)
    assert res_reboot["is_reboot"] is True
