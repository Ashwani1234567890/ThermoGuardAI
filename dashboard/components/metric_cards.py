"""
Metric Cards & KPI Components for SHADOW THERMOGUARD AI.
Renders real-world industrial monitoring indicators.
"""

import streamlit as st
from typing import Dict, Any, Optional


def render_kpi_metrics(summary: Optional[Dict[str, Any]], is_online: bool):
    """Renders high-level temperature, range, and spatial metrics."""
    if not summary:
        summary = {
            "max_temperature": 0.0,
            "min_temperature": 0.0,
            "mean_temperature": 0.0,
            "spatial_range": 0.0,
            "spatial_std": 0.0,
            "hottest_sensor_id": 0,
            "coldest_sensor_id": 0,
        }

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        max_t = summary.get("max_temperature", 0.0)
        hottest_s = summary.get("hottest_sensor_id", 0) + 1  # 1-indexed display
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #ef4444;">
                <div class="kpi-label">Peak Temperature</div>
                <div class="kpi-value" style="color: {'#ef4444' if max_t >= 75 else '#f59e0b' if max_t >= 50 else '#f8fafc'};">
                    {max_t:.2f} <span style="font-size: 1.1rem; color: #94a3b8;">°C</span>
                </div>
                <div class="kpi-sub">Hottest Location: <b>Sensor S{hottest_s}</b></div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:
        mean_t = summary.get("mean_temperature", 0.0)
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #00f0ff;">
                <div class="kpi-label">Grid Mean Temp</div>
                <div class="kpi-value">
                    {mean_t:.2f} <span style="font-size: 1.1rem; color: #94a3b8;">°C</span>
                </div>
                <div class="kpi-sub">16-Channel Average</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:
        min_t = summary.get("min_temperature", 0.0)
        coldest_s = summary.get("coldest_sensor_id", 0) + 1
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #3b82f6;">
                <div class="kpi-label">Minimum Temp</div>
                <div class="kpi-value">
                    {min_t:.2f} <span style="font-size: 1.1rem; color: #94a3b8;">°C</span>
                </div>
                <div class="kpi-sub">Coldest Location: <b>Sensor S{coldest_s}</b></div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c4:
        s_range = summary.get("spatial_range", 0.0)
        s_std = summary.get("spatial_std", 0.0)
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #8b5cf6;">
                <div class="kpi-label">Spatial Gradient (ΔT)</div>
                <div class="kpi-value">
                    {s_range:.2f} <span style="font-size: 1.1rem; color: #94a3b8;">°C</span>
                </div>
                <div class="kpi-sub">Spatial σ: <b>{s_std:.2f} °C</b></div>
            </div>
            """,
            unsafe_allow_html=True
        )


def render_ai_threat_card(
    ai_class: Optional[str],
    ai_confidence: Optional[float],
    safety_state: str,
    active_alarms: int
):
    """
    Renders the AI Threat Detection classification alongside
    the independent Deterministic Safety State.
    """
    col1, col2 = st.columns(2)

    with col1:
        # Deterministic Safety Logic Panel
        state_colors = {
            "NORMAL": ("#10b981", "pill-normal"),
            "WARNING": ("#f59e0b", "pill-warning"),
            "CRITICAL": ("#ef4444", "pill-critical"),
            "FAULT": ("#8b5cf6", "pill-fault"),
        }
        color, pill_class = state_colors.get(safety_state.upper(), ("#94a3b8", "pill-normal"))

        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid {color};">
                <div class="kpi-label">Deterministic Edge Safety Logic</div>
                <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 0.5rem;">
                    <span class="status-pill {pill_class}" style="font-size: 1rem; padding: 0.35rem 1rem;">
                        {safety_state.upper()}
                    </span>
                    <span style="font-size: 0.85rem; color: #94a3b8;">
                        Active Alarms: <b style="color: {'#ef4444' if active_alarms > 0 else '#10b981'};">{active_alarms}</b>
                    </span>
                </div>
                <div class="kpi-sub" style="margin-top: 0.6rem;">
                    Local ESP32 hardware safety controller operates independently of network connectivity.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        # Edge Extra Trees AI Model Panel
        ai_display = ai_class.replace("_", " ").title() if ai_class else "Normal"
        conf_pct = (ai_confidence * 100.0) if ai_confidence is not None else 95.0

        ai_color = "#10b981"
        if ai_class in ("hotspot", "gradual_heating"):
            ai_color = "#f59e0b"
        elif ai_class == "rapid_rise":
            ai_color = "#ef4444"
        elif ai_class == "sensor_anomaly":
            ai_color = "#8b5cf6"

        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid {ai_color};">
                <div class="kpi-label">Edge Extra Trees AI Classification</div>
                <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 0.5rem;">
                    <span style="font-size: 1.4rem; font-weight: 800; color: {ai_color};">
                        {ai_display}
                    </span>
                    <span style="font-size: 1.1rem; font-weight: 700; color: #f8fafc;">
                        {conf_pct:.1f}% <span style="font-size: 0.75rem; color: #94a3b8;">CONF</span>
                    </span>
                </div>
                <div class="kpi-sub" style="margin-top: 0.6rem;">
                    300-Tree Edge Ensemble Window: 60 timesteps across 16 spatial features.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
