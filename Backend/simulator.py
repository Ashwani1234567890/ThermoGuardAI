"""
ThermoGuardAI Telemetry Simulator
Generates realistic 16-channel thermal sensor telemetry for 5 distinct scenarios:
1. normal: Steady ambient conditions with baseline sensor noise.
2. hotspot: Localized heating around a target sensor in the 4x4 matrix.
3. gradual_heating: Linear temperature climb over time across sensors.
4. rapid_rise: Severe, abrupt thermal surge triggering critical alarms.
5. sensor_anomaly: Hardware faults (stuck sensor, open/short circuit, severe noise).

All packets are explicitly tagged with `is_simulated = True`.
"""

import time
import random
import argparse
import logging
import requests
import numpy as np
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple

from backend.communication.protocol import pack_telemetry
import socket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Simulator]: %(message)s"
)
logger = logging.getLogger("thermoguard.simulator")


def temp_to_raw_adc(temp_c: float) -> int:
    """Simulates 12-bit ADC reading for an NTC thermistor in voltage divider."""
    # Approximate inverse mapping: higher temp -> lower NTC resistance -> higher voltage
    # Clamped to 0..4095 (12-bit)
    normalized = (temp_c + 10.0) / 120.0
    adc = int(normalized * 4095)
    return max(0, min(4095, adc))


class ThermalSimulator:
    def __init__(self, device_id: str = "SIM-ESP32-001", ambient_temp: float = 26.5):
        self.device_id = device_id
        self.ambient_temp = ambient_temp
        self.sequence_number = 0
        self.boot_count = 1
        self.start_time = time.time()
        self.sensor_offsets = [random.uniform(-0.25, 0.25) for _ in range(16)]

    def generate_cycle(
        self,
        scenario: str,
        step: int,
        total_steps: int = 60,
        target_sensor: int = 5
    ) -> Dict[str, Any]:
        """
        Generates 16 calibrated temperatures and corresponding ADC values
        for a 4x4 sensor grid.
        """
        self.sequence_number += 1
        uptime_ms = int((time.time() - self.start_time) * 1000)

        # Baseline ambient readings with small Gaussian jitter
        temps = [
            self.ambient_temp + self.sensor_offsets[i] + random.gauss(0, 0.12)
            for i in range(16)
        ]
        statuses = ["valid"] * 16
        safety_state = "NORMAL"
        ai_class = "normal"
        ai_confidence = 0.94

        row_target = target_sensor // 4
        col_target = target_sensor % 4

        # 1. NORMAL
        if scenario == "normal":
            safety_state = "NORMAL"
            ai_class = "normal"
            ai_confidence = round(random.uniform(0.92, 0.98), 3)

        # 2. HOTSPOT
        elif scenario == "hotspot":
            ai_class = "hotspot"
            ai_confidence = round(random.uniform(0.88, 0.96), 3)
            # Center sensor heats up significantly
            temps[target_sensor] += 16.5
            # Heat diffuses to Manhattan-distance-1 adjacent sensors
            for i in range(16):
                r = i // 4
                c = i % 4
                dist = abs(row_target - r) + abs(col_target - c)
                if dist == 1:
                    temps[i] += 4.5
                elif dist == 2:
                    temps[i] += 1.2
            if max(temps) >= 50.0:
                safety_state = "WARNING"

        # 3. GRADUAL HEATING
        elif scenario == "gradual_heating":
            ai_class = "gradual_heating"
            ai_confidence = round(random.uniform(0.85, 0.94), 3)
            progress = min(1.0, step / max(1, total_steps))
            rise = progress * 24.0
            temps[target_sensor] += rise
            for i in range(16):
                if i != target_sensor:
                    temps[i] += rise * 0.35
            if max(temps) >= 50.0:
                safety_state = "WARNING"

        # 4. RAPID RISE
        elif scenario == "rapid_rise":
            ai_class = "rapid_rise"
            ai_confidence = round(random.uniform(0.91, 0.99), 3)
            surge = min(step * 3.8, 55.0)
            temps[target_sensor] += surge
            for i in range(16):
                r = i // 4
                c = i % 4
                if abs(row_target - r) + abs(col_target - c) == 1:
                    temps[i] += surge * 0.3
            if max(temps) >= 75.0:
                safety_state = "CRITICAL"
            elif max(temps) >= 50.0:
                safety_state = "WARNING"

        # 5. SENSOR ANOMALY
        elif scenario == "sensor_anomaly":
            ai_class = "sensor_anomaly"
            ai_confidence = round(random.uniform(0.86, 0.97), 3)
            fault_mode = step % 3
            if fault_mode == 0:
                # Open circuit / high temp spike
                temps[target_sensor] = 115.0
                statuses[target_sensor] = "open_circuit"
                safety_state = "FAULT"
            elif fault_mode == 1:
                # Stuck sensor
                temps[target_sensor] = 88.0
                statuses[target_sensor] = "stuck"
                safety_state = "FAULT"
            else:
                # Noisy sensor
                temps[target_sensor] += random.gauss(0, 18.0)
                statuses[target_sensor] = "noisy"
                safety_state = "FAULT"

        readings = []
        for i in range(16):
            t = round(float(temps[i]), 2)
            adc = temp_to_raw_adc(t)
            readings.append({
                "sensor_id": i,
                "temperature": t,
                "raw_adc_value": adc,
                "sensor_status": statuses[i]
            })

        return {
            "device_id": self.device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "readings": readings,
            "sequence_number": self.sequence_number,
            "boot_count": self.boot_count,
            "uptime_ms": uptime_ms,
            "deterministic_safety_state": safety_state,
            "ai_prediction": {
                "class_index": ["gradual_heating", "hotspot", "normal", "rapid_rise", "sensor_anomaly"].index(ai_class),
                "class_name": ai_class,
                "confidence": ai_confidence,
                "probabilities": [0.2] * 5
            },
            "is_simulated": True
        }

    def send_http(self, payload: Dict[str, Any], endpoint_url: str) -> bool:
        """Sends telemetry over REST API."""
        try:
            resp = requests.post(endpoint_url, json=payload, timeout=3.0)
            if resp.status_code in (200, 201):
                logger.info(
                    f"[REST] Sent seq {payload['sequence_number']}: "
                    f"State={payload['deterministic_safety_state']} | "
                    f"AI={payload['ai_prediction']['class_name']} ({payload['ai_prediction']['confidence']*100:.0f}%)"
                )
                return True
            else:
                logger.warning(f"[REST] HTTP {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"[REST] Failed to send telemetry: {e}")
            return False

    def send_udp(self, payload: Dict[str, Any], host: str = "127.0.0.1", port: int = 5005) -> bool:
        """Encodes and transmits telemetry as binary UDP datagram."""
        try:
            temps = [r["temperature"] for r in payload["readings"]]
            adcs = [r["raw_adc_value"] for r in payload["readings"]]
            statuses = [r["sensor_status"] for r in payload["readings"]]
            ai = payload["ai_prediction"]

            packet_bytes = pack_telemetry(
                device_id=payload["device_id"],
                sequence_number=payload["sequence_number"],
                boot_count=payload["boot_count"],
                uptime_ms=payload["uptime_ms"],
                deterministic_safety_state=payload["deterministic_safety_state"],
                ai_class=ai["class_name"] if ai else None,
                ai_confidence=ai["confidence"] if ai else None,
                temperatures=temps,
                raw_adcs=adcs,
                statuses=statuses
            )

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(packet_bytes, (host, port))
            sock.close()
            logger.info(
                f"[UDP] Transmitted {len(packet_bytes)} bytes | seq={payload['sequence_number']} to {host}:{port}"
            )
            return True
        except Exception as e:
            logger.error(f"[UDP] Failed to send datagram: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="ThermoGuardAI Telemetry Simulator")
    parser.add_argument("--device", type=str, default="SIM-ESP32-001", help="Device identifier")
    parser.add_argument("--scenario", type=str, default="normal",
                        choices=["normal", "hotspot", "gradual_heating", "rapid_rise", "sensor_anomaly", "all"],
                        help="Thermal simulation scenario")
    parser.add_argument("--cycles", type=int, default=10, help="Number of telemetry cycles (0 for infinite)")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between cycles")
    parser.add_argument("--mode", type=str, default="http", choices=["http", "udp"], help="Transport mode")
    parser.add_argument("--url", type=str, default="http://127.0.0.1:8000/api/telemetry", help="REST API endpoint")
    parser.add_argument("--udp-host", type=str, default="127.0.0.1", help="UDP target host")
    parser.add_argument("--udp-port", type=int, default=5005, help="UDP target port")
    args = parser.parse_args()

    simulator = ThermalSimulator(device_id=args.device)
    logger.info(f"Starting Telemetry Simulator: device={args.device}, scenario={args.scenario}, mode={args.mode}")

    scenarios = ["normal", "hotspot", "gradual_heating", "rapid_rise", "sensor_anomaly"] if args.scenario == "all" else [args.scenario]

    cycle_count = 0
    try:
        while True:
            for sc in scenarios:
                steps = args.cycles if args.cycles > 0 else 60
                for step in range(steps):
                    payload = simulator.generate_cycle(scenario=sc, step=step, total_steps=steps)
                    if args.mode == "http":
                        simulator.send_http(payload, args.url)
                    else:
                        simulator.send_udp(payload, host=args.udp_host, port=args.udp_port)

                    cycle_count += 1
                    if args.cycles > 0 and cycle_count >= args.cycles:
                        logger.info("Simulation completed.")
                        return

                    time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("Simulation halted by user.")


if __name__ == "__main__":
    main()
