"""
Interactive Plotly Temperature Charts for SHADOW THERMOGUARD AI.
Supports per-sensor history, spatial comparisons, and distribution analytics.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from typing import List, Dict, Any, Optional


def render_temperature_history_chart(
    readings: Optional[List[Dict[str, Any]]],
    selected_sensors: Optional[List[int]] = None
):
    """
    Renders time-series temperature curves for selected sensors.
    Uses real backend data from GET /api/telemetry/history/{device_id}.
    """
    if not readings:
        st.info("No historical readings recorded yet for this device.")
        return

    df = pd.DataFrame(readings)
    df["sensor_label"] = df["sensor_id"].apply(lambda sid: f"S{sid + 1}")
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    if selected_sensors:
        labels = [f"S{s}" for s in selected_sensors]
        df = df[df["sensor_label"].isin(labels)]

    fig = px.line(
        df,
        x="timestamp",
        y="temperature",
        color="sensor_label",
        markers=True,
        labels={"timestamp": "Acquisition Time (UTC)", "temperature": "Temperature (°C)", "sensor_label": "Sensor"},
        title="Thermal Trend Across Acquisition Cycles"
    )

    # Safety Threshold Reference Lines
    fig.add_hline(y=50.0, line_dash="dash", line_color="#f59e0b", annotation_text="Warning (50°C)", annotation_font_color="#f59e0b")
    fig.add_hline(y=75.0, line_dash="dash", line_color="#ef4444", annotation_text="Critical (75°C)", annotation_font_color="#ef4444")

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=380,
        margin=dict(l=10, r=10, t=35, b=10),
        xaxis=dict(gridcolor="#1e293b", tickfont=dict(color="#94a3b8")),
        yaxis=dict(gridcolor="#1e293b", tickfont=dict(color="#94a3b8")),
        legend=dict(font=dict(color="#94a3b8"), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)


def render_sensor_comparison_bar(grid_4x4: Optional[List[List[float]]]):
    """Renders a comparative bar chart for all 16 sensors S1–S16 in the current cycle."""
    if not grid_4x4 or len(grid_4x4) < 4:
        return

    temps = []
    labels = []
    colors = []

    for r in range(4):
        for c in range(4):
            idx = r * 4 + c + 1
            t = grid_4x4[r][c]
            labels.append(f"S{idx}")
            temps.append(t)
            if t >= 75.0:
                colors.append("#ef4444")
            elif t >= 50.0:
                colors.append("#f59e0b")
            else:
                colors.append("#10b981")

    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=temps,
                marker_color=colors,
                text=[f"{t:.1f}°C" for t in temps],
                textposition="auto"
            )
        ]
    )

    fig.add_hline(y=50.0, line_dash="dot", line_color="#f59e0b")
    fig.add_hline(y=75.0, line_dash="dot", line_color="#ef4444")

    fig.update_layout(
        title="16-Channel Temperature Profile (S1–S16)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=300,
        margin=dict(l=10, r=10, t=35, b=10),
        xaxis=dict(tickfont=dict(color="#94a3b8")),
        yaxis=dict(title="Temperature (°C)", gridcolor="#1e293b", tickfont=dict(color="#94a3b8"))
    )

    st.plotly_chart(fig, use_container_width=True)


def render_spatial_distribution_chart(grid_4x4: Optional[List[List[float]]]):
    """Renders distribution histogram showing temperature variance across the 4x4 grid."""
    if not grid_4x4 or len(grid_4x4) < 4:
        return

    flattened = [temp for row in grid_4x4 for temp in row]
    df = pd.DataFrame({"temperature": flattened})

    fig = px.histogram(
        df,
        x="temperature",
        nbins=12,
        title="Grid Spatial Temperature Distribution",
        labels={"temperature": "Temperature (°C)"},
        color_discrete_sequence=["#00f0ff"]
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=280,
        margin=dict(l=10, r=10, t=35, b=10),
        xaxis=dict(gridcolor="#1e293b", tickfont=dict(color="#94a3b8")),
        yaxis=dict(title="Sensor Count", gridcolor="#1e293b", tickfont=dict(color="#94a3b8"))
    )

    st.plotly_chart(fig, use_container_width=True)
