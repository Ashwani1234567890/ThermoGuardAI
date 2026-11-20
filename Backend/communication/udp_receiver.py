import asyncio
import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.services.telemetry_service import TelemetryService
from backend.services.device_service import DeviceService
from backend.communication.protocol import (
    unpack_telemetry,
    PacketTracker,
    ProtocolError,
)

logger = logging.getLogger("thermoguard.udp")


class UDPTelemetryReceiver(asyncio.DatagramProtocol):
    """
    Asynchronous UDP receiver for high-throughput ESP32 binary telemetry.
    Validates packet length, CRC32, sequence numbers, and persists readings
    via TelemetryService in a dedicated session context.
    """
    def __init__(self):
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.tracker = PacketTracker()
        self.total_received = 0
        self.total_corrupted = 0
        self.total_duplicates = 0

    def connection_made(self, transport: asyncio.DatagramTransport):
        self.transport = transport
        sock = transport.get_extra_info("socket")
        addr = sock.getsockname() if sock else "unknown"
        logger.info(f"UDP Telemetry Receiver listening on {addr}")

    def datagram_received(self, data: bytes, addr: tuple):
        self.total_received += 1
        client_ip, client_port = addr[0], addr[1]

        try:
            packet = unpack_telemetry(data)
        except ProtocolError as err:
            self.total_corrupted += 1
            logger.warning(
                f"Rejected corrupted UDP packet from {client_ip}:{client_port}: {err}"
            )
            return
        except Exception as err:
            self.total_corrupted += 1
            logger.error(f"Unexpected error decoding packet from {client_ip}:{client_port}: {err}")
            return

        # Track sequence and reboot state
        track_info = self.tracker.process_packet(
            device_id=packet.device_id,
            boot_count=packet.boot_count,
            sequence_number=packet.sequence_number
        )

        if track_info["is_reboot"]:
            logger.warning(
                f"Device reboot detected for {packet.device_id}! New boot count: {packet.boot_count}"
            )

        if track_info["is_duplicate"]:
            self.total_duplicates += 1
            logger.debug(
                f"Duplicate packet seq {packet.sequence_number} dropped for {packet.device_id}"
            )
            return

        if track_info["is_gap"]:
            logger.info(
                f"Packet gap detected for {packet.device_id}: missed {track_info['gap_count']} packets"
            )

        # Ingest and persist telemetry
        db: Session = SessionLocal()
        try:
            payload = packet.to_payload()
            DeviceService.update_last_seen(
                db=db,
                device_id=packet.device_id,
                ip_address=client_ip,
                boot_count=packet.boot_count,
                status="online"
            )
            TelemetryService.save_telemetry(db, payload)
        except Exception as err:
            logger.error(f"Failed to persist UDP telemetry for {packet.device_id}: {err}")
            db.rollback()
        finally:
            db.close()

    def error_received(self, exc: Exception):
        logger.error(f"UDP Receiver socket error: {exc}")


async def start_udp_receiver(host: str = "0.0.0.0", port: int = 5005) -> Tuple[asyncio.DatagramTransport, UDPTelemetryReceiver]:
    """Factory function to bind and start UDP receiver as an asyncio background service."""
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPTelemetryReceiver(),
        local_addr=(host, port)
    )
    return transport, protocol
