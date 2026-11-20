"""
Page 4: System Architecture & Hardware Specs for SHADOW THERMOGUARD AI.
Documents the complete physical dual-bank architecture, 300-tree Extra Trees ML engine,
deterministic safety limits, and existing backend REST endpoints.
"""

import streamlit as st
import time
from pathlib import Path

from dashboard.config import config
from dashboard.api_client import BackendAPIClient
from dashboard.components import render_sidebar

st.set_page_config(
    page_title=f"{config.APP_NAME} – System Info",
    page_icon="⚙️",
    layout="wide"
)

# Load CSS
css_path = Path(__file__).parent.parent / "assets" / "style.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

if "api_client" not in st.session_state:
    st.session_state["api_client"] = BackendAPIClient(base_url=config.DEFAULT_BACKEND_URL)
api_client: BackendAPIClient = st.session_state["api_client"]

backend_url, selected_device, _, _ = render_sidebar(api_client)

st.title("⚙️ System Architecture & Hardware Specifications")
st.caption("Decentralized Edge Intelligence & Deterministic Safety Separation Architecture")

st.divider()

# 1. Hardware Subsystem Specifications
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🎛️ Dual-Bank Multiplexer Hardware")
    st.markdown(
        """
        - **Microcontroller**: ESP32 (Tensilica Xtensa Dual-Core 240 MHz).
        - **Sensor Array**: 16 NTC 10kΩ Thermistors in a 4×4 spatial matrix.
        - **Dual-Bank Analog Multiplexing**:
          - **Bank A (Sensors S1–S8)**: Routed to ADC input **GPIO34**.
          - **Bank B (Sensors S9–S16)**: Routed to ADC input **GPIO35**.
        - **Shared Select Lines**: GPIO16 (S0), GPIO17 (S1), GPIO18 (S2), GPIO19 (S3).
        - **ADC Configuration**: 12-bit resolution (0–4095), 11dB attenuation.
        - **Sample Averaging**: 5 ADC readings averaged per channel with 50µs settling delay.
        """
    )

with col2:
    st.markdown("### 🤖 Extra Trees Edge AI Inference")
    st.markdown(
        """
        - **Ensemble Architecture**: Extra Trees Classifier (300 Decision Trees).
        - **Edge Deployment**: C++ compiled direct tree traversal (`thermal_model.h`).
        - **Window Buffer**: Circular buffer storing 60 timesteps × 16 sensors (`WINDOW_SIZE = 60`).
        - **Extracted Features (16 Total)**:
          - *Spatial*: Mean, Max, Min, Spatial Range, Spatial Std Dev, Max Sensor Mean, Min Sensor Mean.
          - *Temporal*: Mean Rate of Change, Max/Min Rate of Change, Temporal Std Dev, Overall Temp Rise.
          - *Health*: Stable Sensor Std Dev, Noisy Sensor Std Dev, Sensor Variation Range, Stuck Sensor Count.
        - **5 Target Classes**: `normal`, `hotspot`, `gradual_heating`, `rapid_rise`, `sensor_anomaly`.
        """
    )

st.divider()

# 2. Independent Deterministic Safety vs AI Matrix
st.markdown("### 🛡️ Safety & AI Independence Architecture")
st.markdown(
    """
    To guarantee industrial safety compliance, **deterministic hardware cut-offs remain completely decoupled from AI inference**:
    """
)

st.markdown(
    """
    | Function | Deterministic Safety Controller (ESP32) | Extra Trees ML Classifier (Edge AI) |
    |---|---|---|
    | **Execution Location** | Local firmware loop on ESP32 | Edge circular window buffer (60 samples) |
    | **Decision Criteria** | Hard thresholds (T > 50°C, T > 75°C, dT/dt > 2°C/s) | 300 Decision Trees pattern classification |
    | **Output Target** | Physical cut-off relays, audible buzzer, warning LED | Diagnostic telemetry & classification confidence |
    | **Network Dependency** | **ZERO** (operates fully air-gapped) | **ZERO** (runs completely onboard ESP32) |
    | **Backend Role** | Ingests, persists, and visualizes alarms | Ingests confidence & advisory predictions |
    """
)

st.divider()

# 3. Existing Backend REST Endpoint Catalog
st.markdown("### 🔌 Backend REST API Endpoint Verification")
st.markdown("Below is the catalog of existing backend REST endpoints consumed by this dashboard:")

endpoints = [
    ("GET", "/", "Root health and identity probe"),
    ("GET", "/api/health", "Comprehensive health check (DB connectivity, devices, active alarms)"),
    ("GET", "/api/devices", "List all registered edge devices"),
    ("GET", "/api/devices/{device_id}", "Retrieve metadata for a specific edge device"),
    ("GET", "/api/devices/{device_id}/status", "Check real-time online/offline status and last seen"),
    ("POST", "/api/devices/register", "Register or update edge sensor device"),
    ("POST", "/api/telemetry", "Ingest a single 16-channel acquisition cycle"),
    ("POST", "/api/telemetry/batch", "Batch ingestion of multiple acquisition cycles"),
    ("GET", "/api/telemetry/latest/{device_id}", "Retrieve latest 4x4 matrix and spatial statistics"),
    ("GET", "/api/telemetry/history/{device_id}", "Query historical readings with pagination and sensor filters"),
    ("GET", "/api/events", "List and filter thermal threat alarms and anomalies"),
    ("GET", "/api/events/{event_id}", "Retrieve details of a single thermal event"),
    ("PATCH", "/api/events/{event_id}/acknowledge", "Acknowledge an active thermal alarm"),
    ("WS", "/ws/telemetry/{device_id}", "WebSocket live telemetry streaming endpoint"),
]

endpoint_rows = []
for method, path, desc in endpoints:
    endpoint_rows.append({
        "HTTP Method": method,
        "Endpoint Path": path,
        "Description": desc,
        "Backend Status": "✅ ACTIVE IN BACKEND"
    })

st.dataframe(endpoint_rows, use_container_width=True, hide_index=True)
