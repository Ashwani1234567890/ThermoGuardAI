"""
Page 1: Live Thermal Monitoring for SHADOW THERMOGUARD AI.
Focused real-time 4x4 grid view, tile matrix, color scales, and sensor spotlights.
"""

import time
import streamlit as st
import pandas as pd
from pathlib import Path

from dashboard.config import config
from dashboard.api_client import BackendAPIClient
from dashboard.components import (
    render_sidebar,
    render_thermal_heatmap,
    render_sensor_tile_grid,
    render_kpi_metrics,
    render_device_status_banner,
)

st.set_page_config(
    page_title=f"{config.APP_NAME} – Live Monitoring",
    page_icon="🔥",
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

backend_url, selected_device, auto_refresh, refresh_interval = render_sidebar(api_client)

st.title("🔥 Live 4×4 Thermal Grid Monitoring")
st.caption(f"Continuous real-time telemetry from edge unit: `{selected_device}`")

# Fetch latest telemetry
_, dev_status, _ = api_client.get_device_status(selected_device)
_, latest_grid, err = api_client.get_latest_telemetry(selected_device)

render_device_status_banner(dev_status, selected_device)

summary = latest_grid.get("summary") if latest_grid else None
is_online = dev_status.get("is_online", False) if dev_status else False
render_kpi_metrics(summary, is_online=is_online)

st.divider()

if latest_grid and "grid_4x4" in latest_grid:
    grid_matrix = latest_grid["grid_4x4"]

    col_controls, col_spotlight = st.columns([6, 4])
    with col_controls:
        color_scheme = st.selectbox(
            "Heatmap Color Palette",
            options=["Inferno", "Turbo", "Jet", "Viridis", "Hot", "Magma"],
            index=0,
            help="Select scientific or thermal visualization palette."
        )
    with col_spotlight:
        hottest_id = summary.get("hottest_sensor_id", 0) + 1 if summary else 1
        peak_temp = summary.get("max_temperature", 0.0) if summary else 0.0
        st.markdown(
            f"""
            <div style="background: #111827; border: 1px solid #334155; border-radius: 8px; padding: 0.6rem 1rem;">
                <span style="font-size: 0.8rem; color: #94a3b8;">ACTIVE HOTSPOT SPOTLIGHT:</span>
                <b style="color: #ef4444; font-size: 1.1rem; margin-left: 0.5rem;">Sensor S{hottest_id}</b>
                <span style="color: #f8fafc; margin-left: 0.5rem;">({peak_temp:.1f} °C)</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    col_heat, col_tiles = st.columns([5, 5])

    with col_heat:
        st.markdown("#### 2D Surface Heatmap")
        render_thermal_heatmap(grid_matrix, color_scale=color_scheme)

    with col_tiles:
        st.markdown("#### Physical Sensor Channel Layout")
        render_sensor_tile_grid(grid_matrix)

    st.divider()

    # Detailed Per-Sensor Channel Table
    st.markdown("#### 📋 16-Channel Telemetry Registry")
    records = []
    mean_val = summary.get("mean_temperature", 0.0) if summary else 0.0
    for r in range(4):
        for c in range(4):
            idx = r * 4 + c + 1
            t = grid_matrix[r][c]
            delta = t - mean_val
            bank = "Bank A (GPIO34)" if idx <= 8 else "Bank B (GPIO35)"
            status_text = "CRITICAL" if t >= 75.0 else "WARNING" if t >= 50.0 else "NORMAL"

            records.append({
                "Sensor ID": f"S{idx:02d}",
                "Grid Row": r,
                "Grid Col": c,
                "Hardware Bank": bank,
                "Temperature (°C)": f"{t:.2f}",
                "Delta From Mean (°C)": f"{delta:+.2f}",
                "Status": status_text
            })

    st.dataframe(pd.DataFrame(records), use_container_width=True, hide_index=True)

else:
    st.warning(f"No telemetry data currently available for device `{selected_device}`.")

if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
