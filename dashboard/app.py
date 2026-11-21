"""
SHADOW THERMOGUARD AI – Frontend Application
Decentralized Edge Intelligence for Real-Time Thermal Threat Detection

Main Dashboard Overview. Connects strictly through existing backend REST APIs.
Does NOT modify or connect directly to any backend files or SQLite databases.
"""

import time
import streamlit as st
from pathlib import Path

from config import config
from dashboard.api_client import BackendAPIClient
from dashboard.components import (
    render_sidebar,
    render_kpi_metrics,
    render_ai_threat_card,
    render_thermal_heatmap,
    render_sensor_tile_grid,
    render_temperature_history_chart,
    render_sensor_comparison_bar,
    render_alerts_section,
    render_device_status_banner,
)

# Page Setup
st.set_page_config(
    page_title=f"{config.APP_NAME} – Overview",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Industrial Dark CSS
css_path = Path(__file__).parent / "assets" / "style.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialize API Client in Session State
if "api_client" not in st.session_state:
    st.session_state["api_client"] = BackendAPIClient(base_url=config.DEFAULT_BACKEND_URL)

api_client: BackendAPIClient = st.session_state["api_client"]

# Render Sidebar Navigation & Control Panel
backend_url, selected_device, auto_refresh, refresh_interval = render_sidebar(api_client)

# Header Banner
st.markdown(
    f"""
    <div class="main-title-container">
        <h1 class="main-title">{config.APP_NAME}</h1>
        <div class="main-subtitle">{config.APP_SUBTITLE}</div>
    </div>
    """,
    unsafe_allow_html=True
)

# Health Probe
is_healthy, health_data, health_err = api_client.get_health()

if not is_healthy:
    st.markdown(
        f"""
        <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; border-radius: 8px; padding: 1.25rem; color: #fca5a5; margin-bottom: 1.5rem;">
            <h4 style="margin: 0 0 0.5rem 0; color: #ef4444;">🚨 BACKEND SERVICE UNAVAILABLE</h4>
            <p style="margin: 0; font-size: 0.9rem;">
                Unable to establish HTTP connection with the FastAPI backend at <code>{backend_url}</code>.<br/>
                <b>Details:</b> {health_err}
            </p>
            <p style="margin: 0.75rem 0 0 0; font-size: 0.85rem; color: #cbd5e1;">
                Please ensure the existing backend is running: <code>python -m uvicorn backend.main:app --port 8000</code>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.stop()

# Query Data for Selected Device
_, dev_status, _ = api_client.get_device_status(selected_device)
_, latest_grid, _ = api_client.get_latest_telemetry(selected_device)
_, active_events, _ = api_client.get_events(device_id=selected_device, acknowledged=False, page_size=5)
_, history_data, _ = api_client.get_telemetry_history(device_id=selected_device, page_size=60)

# 1. Device Status Banner
render_device_status_banner(dev_status, selected_device)

# 2. Main KPI Metrics
summary = latest_grid.get("summary") if latest_grid else None
is_online = dev_status.get("is_online", False) if dev_status else False
render_kpi_metrics(summary, is_online=is_online)

st.write("")

# 3. AI Threat & Deterministic Safety Classification
safety_state = latest_grid.get("safety_state", "NORMAL") if latest_grid else "NORMAL"
ai_class = latest_grid.get("ai_class") if latest_grid else None
ai_conf = latest_grid.get("ai_confidence") if latest_grid else None
active_count = health_data.get("active_alarms", len(active_events or []))
render_ai_threat_card(ai_class, ai_conf, safety_state, active_count)

st.divider()

# 4. Thermal Grid Visualizations
col_grid, col_analytics = st.columns([5, 4])

with col_grid:
    st.markdown("### 🔲 4×4 Sensor Grid Heatmap")
    grid_matrix = latest_grid.get("grid_4x4") if latest_grid else None

    if grid_matrix:
        render_thermal_heatmap(grid_matrix)
        with st.expander("Physical 4x4 Sensor Tile Layout", expanded=False):
            render_sensor_tile_grid(grid_matrix)
    else:
        st.markdown(
            f"""
            <div style="background: #111827; border: 1px dashed #334155; border-radius: 8px; padding: 2.5rem; text-align: center; color: #94a3b8;">
                📡 <b>Awaiting Telemetry:</b> No 16-channel acquisition cycles recorded for <code>{selected_device}</code>.<br/>
                <span style="font-size: 0.8rem; color: #64748b;">
                    Start the telemetry generator to stream test cycles:<br/>
                    <code>python -m backend.simulator --device {selected_device} --scenario hotspot</code>
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

with col_analytics:
    st.markdown("### 📊 Spatial Thermal Profile")
    if grid_matrix:
        render_sensor_comparison_bar(grid_matrix)
    else:
        st.info("Spatial analytics will appear once telemetry arrives.")

st.divider()

# 5. Real-Time Temperature History Trend
st.markdown("### 📈 Recent Temperature History (60 Acquisition Timesteps)")
if history_data and history_data.get("readings"):
    render_temperature_history_chart(history_data["readings"])
else:
    st.info(f"No historical telemetry records logged for {selected_device} yet.")

st.divider()

# 6. Active Alarms & Threat Management
st.markdown("### 🚨 Active Thermal Alarms & Anomaly Events")
render_alerts_section(api_client, active_events)

# Automatic Telemetry Refresh
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
