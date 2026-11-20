"""
Frontend Configuration for SHADOW THERMOGUARD AI.
Manages backend endpoints, color palettes, thermal thresholds, and dashboard defaults.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardConfig:
    # Application Branding
    APP_NAME: str = "SHADOW THERMOGUARD AI"
    APP_SUBTITLE: str = "Decentralized Edge Intelligence for Real-Time Thermal Threat Detection"
    APP_VERSION: str = "2.0.0"

    # Backend Connection
    DEFAULT_BACKEND_URL: str = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    REQUEST_TIMEOUT_SECONDS: float = 3.5

    # Hardware & Grid Architecture
    GRID_ROWS: int = 4
    GRID_COLS: int = 4
    TOTAL_SENSORS: int = 16
    DEFAULT_DEVICE_ID: str = "ESP32-DEV-001"

    # Deterministic Safety Thresholds (°C)
    NORMAL_TEMP_MAX: float = 45.0
    WARNING_TEMP_THRESHOLD: float = 50.0
    CRITICAL_TEMP_THRESHOLD: float = 75.0

    # Auto-Refresh Defaults
    DEFAULT_REFRESH_INTERVAL: int = 3  # seconds
    MIN_REFRESH_INTERVAL: int = 1
    MAX_REFRESH_INTERVAL: int = 15

    # Industrial Theme Color Palette
    BG_COLOR: str = "#0B0F19"
    CARD_BG: str = "#111827"
    ACCENT_CYAN: str = "#00F0FF"
    ACCENT_BLUE: str = "#3B82F6"
    NORMAL_GREEN: str = "#10B981"
    WARNING_ORANGE: str = "#F59E0B"
    CRITICAL_RED: str = "#EF4444"
    FAULT_PURPLE: str = "#8B5CF6"


config = DashboardConfig()
