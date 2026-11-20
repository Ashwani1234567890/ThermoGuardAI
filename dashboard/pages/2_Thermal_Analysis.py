"""
Page 2: Thermal Threat & Trend Analysis for SHADOW THERMOGUARD AI.
Deep temporal and spatial analysis over 60-sample feature windows and per-sensor trajectories.
"""

import streamlit as st
import pandas as pd
from pathlib import Path

from dashboard.config import config
from dashboard.api_client import BackendAPIClient
from dashboard.components import (
    render_sidebar,
    render_temperature_history_chart,
    render_sensor_comparison_bar,
    render_spatial_distribution_chart,
)

st.set_page_config(
    page_title=f"{config.APP_NAME} – Thermal Analysis",
    page_icon="📈",
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

st.title("📈 Thermal Threat & Trend Analysis")
st.caption(f"Spatial gradient, temporal rate-of-change, and sensor health analytics for `{selected_device}`")

# Fetch latest telemetry and history
_, latest_grid, _ = api_client.get_latest_telemetry(selected_device)
_, history_data, _ = api_client.get_telemetry_history(selected_device, page_size=200)

readings = history_data.get("readings", []) if history_data else []

if readings:
    st.markdown("### 🔍 Historical Time-Series Trajectory")

    # Sensor Multi-Select Filter
    sensor_options = list(range(1, 17))
    selected_sensors = st.multiselect(
        "Filter Specific Sensor Channels",
        options=sensor_options,
        default=[1, 6, 11, 16],
        help="Select any combination of sensors S1–S16 to plot."
    )

    render_temperature_history_chart(readings, selected_sensors=selected_sensors)

    st.divider()

    # Spatial Distribution & Bar Comparisons
    col1, col2 = st.columns(2)

    with col1:
        grid_matrix = latest_grid.get("grid_4x4") if latest_grid else None
        st.markdown("### 📊 16-Sensor Instantaneous Profile")
        render_sensor_comparison_bar(grid_matrix)

    with col2:
        st.markdown("### 📐 Spatial Temperature Histogram")
        render_spatial_distribution_chart(grid_matrix)

    st.divider()

    # Summary Statistics & Edge ML Feature Alignment
    st.markdown("### 🧮 Edge ML Feature Alignment (60-Window Feature Vector)")
    st.markdown(
        """
        The ESP32 firmware calculates 16 spatial, temporal, and health features across a 60-timestep window
        to feed into the onboard **Extra Trees 300-tree ensemble**. Below are the key metrics computed from recent telemetry:
        """
    )

    df_hist = pd.DataFrame(readings)
    if not df_hist.empty:
        f_mean = df_hist["temperature"].mean()
        f_max = df_hist["temperature"].max()
        f_min = df_hist["temperature"].min()
        f_std = df_hist["temperature"].std()
        f_range = f_max - f_min

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Temporal Mean", f"{f_mean:.2f} °C")
        c2.metric("Temporal Peak", f"{f_max:.2f} °C")
        c3.metric("Temporal Min", f"{f_min:.2f} °C")
        c4.metric("Temporal Std (σ)", f"{f_std:.2f} °C")
        c5.metric("Temporal Range (Δ)", f"{f_range:.2f} °C")

else:
    st.info(f"No historical telemetry data available yet for `{selected_device}`. Start the simulator to populate time-series records.")
