"""
4x4 Thermal Monitoring Grid & Heatmap Visualizations for SHADOW THERMOGUARD AI.
Supports both Plotly 2D heatmap and physical 4x4 tile layout matching dual-bank NTC hardware.
"""

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from typing import List, Optional


def render_thermal_heatmap(
    grid_4x4: Optional[List[List[float]]],
    color_scale: str = "Inferno",
    min_temp: float = 20.0,
    max_temp: float = 85.0
):
    """
    Renders an interactive Plotly 2D thermal heatmap representing the 4x4 sensor matrix.
    Row 0: S1–S4 | Row 1: S5–S8 | Row 2: S9–S12 | Row 3: S13–S16.
    """
    if not grid_4x4 or len(grid_4x4) < 4:
        st.warning("⚠️ 4×4 Grid telemetry is currently unavailable.")
        return

    grid_matrix = np.array(grid_4x4, dtype=float)

    # Sensor label annotations (S1 to S16, 1-indexed)
    text_matrix = [
        [f"S{r * 4 + c + 1}<br><b>{grid_matrix[r][c]:.1f}°C</b>" for c in range(4)]
        for r in range(4)
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=grid_matrix,
            x=["Col 0", "Col 1", "Col 2", "Col 3"],
            y=["Row 0", "Row 1", "Row 2", "Row 3"],
            colorscale=color_scale,
            zmin=min_temp,
            zmax=max(max_temp, float(np.max(grid_matrix)) + 2.0),
            text=text_matrix,
            texttemplate="%{text}",
            textfont={"size": 14, "color": "white", "family": "Inter, sans-serif"},
            colorbar=dict(
                title=dict(text="Temp (°C)", side="top", font=dict(color="#94a3b8")),
                tickfont=dict(color="#94a3b8"),
                outlinecolor="#1e293b",
                len=0.9
            ),
            hoverongaps=False,
            hovertemplate="Sensor %{text}<extra></extra>"
        )
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        height=420,
        xaxis=dict(
            tickfont=dict(color="#94a3b8"),
            gridcolor="#1e293b",
            showgrid=False
        ),
        yaxis=dict(
            tickfont=dict(color="#94a3b8"),
            gridcolor="#1e293b",
            showgrid=False,
            autorange="reversed"  # Matrix Row 0 on top
        )
    )

    st.plotly_chart(fig, use_container_width=True)


def render_sensor_tile_grid(grid_4x4: Optional[List[List[float]]]):
    """
    Renders 16 individual hardware sensor cards in a 4x4 responsive layout.
    Displays sensor ID (S1–S16), Bank mapping (Bank A vs Bank B), and temperature status.
    """
    if not grid_4x4 or len(grid_4x4) < 4:
        st.info("No sensor reading values to display in tile grid.")
        return

    st.markdown("##### 🔲 Physical 4×4 Sensor Matrix (Bank A: S1–S8 | Bank B: S9–S16)")

    for row in range(4):
        cols = st.columns(4)
        for col in range(4):
            sensor_idx = row * 4 + col
            sensor_id = sensor_idx + 1
            temp = grid_4x4[row][col]

            # Dual-bank allocation: S1-S8 (Bank A / GPIO34), S9-S16 (Bank B / GPIO35)
            bank_label = "Bank A (GPIO34)" if sensor_id <= 8 else "Bank B (GPIO35)"

            # Risk level color calculation
            if temp >= 75.0:
                card_border = "#ef4444"
                text_color = "#ef4444"
                status_icon = "🔴 CRITICAL"
            elif temp >= 50.0:
                card_border = "#f59e0b"
                text_color = "#f59e0b"
                status_icon = "🟡 WARNING"
            else:
                card_border = "#10b981"
                text_color = "#10b981"
                status_icon = "🟢 NORMAL"

            with cols[col]:
                st.markdown(
                    f"""
                    <div class="sensor-cell-card" style="border-top: 3px solid {card_border};">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span class="sensor-id-label">S{sensor_id}</span>
                            <span style="font-size: 0.65rem; color: #64748b;">{status_icon}</span>
                        </div>
                        <div class="sensor-temp-display" style="color: {text_color};">
                            {temp:.1f} <span style="font-size: 0.75rem; color: #94a3b8;">°C</span>
                        </div>
                        <div class="sensor-adc-display">
                            {bank_label}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        st.write("")  # Margin between rows
