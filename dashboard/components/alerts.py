"""
Thermal Threat Alerts and Event Management Component.
Provides interactive filtering and operator alarm acknowledgment via PATCH /api/events/{id}/acknowledge.
"""

import streamlit as st
from typing import List, Dict, Any, Optional
from dashboard.api_client import BackendAPIClient


def render_alerts_section(
    api_client: BackendAPIClient,
    events: Optional[List[Dict[str, Any]]],
    operator_name: str = "Operator"
):
    """
    Renders the active threat alerts list with acknowledge buttons.
    """
    if not events:
        st.markdown(
            """
            <div style="background: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 1.5rem; text-align: center; color: #10b981;">
                ✅ <b>ALL SYSTEMS NOMINAL:</b> No active alarms or unresolved thermal anomalies.
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    for ev in events:
        event_id = ev.get("id")
        severity = ev.get("severity", "WARNING").upper()
        event_type = ev.get("event_type", "Anomaly")
        temp = ev.get("temperature", 0.0)
        desc = ev.get("description", "No description provided")
        timestamp = ev.get("timestamp", "Unknown")
        is_acked = ev.get("acknowledged", False)
        sensor = ev.get("affected_sensor")

        # Severity styling
        severity_colors = {
            "CRITICAL": "#ef4444",
            "WARNING": "#f59e0b",
            "FAULT": "#8b5cf6",
            "NORMAL": "#10b981",
        }
        color = severity_colors.get(severity, "#94a3b8")

        with st.container():
            st.markdown(
                f"""
                <div style="background: #111827; border-left: 4px solid {color}; border-top: 1px solid #1f2937; border-right: 1px solid #1f2937; border-bottom: 1px solid #1f2937; border-radius: 6px; padding: 0.85rem 1rem; margin-bottom: 0.6rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 800; color: {color}; font-size: 0.95rem;">{severity} &bull; {event_type.upper()}</span>
                        <span style="font-size: 0.75rem; color: #64748b;">Event #{event_id} | {timestamp}</span>
                    </div>
                    <div style="color: #cbd5e1; font-size: 0.9rem; margin-top: 0.35rem;">
                        {desc} (Trigger Temp: <b>{temp:.1f}°C</b>{f' on Sensor S{sensor+1}' if sensor is not None else ''})
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            col_ack, col_info = st.columns([2, 8])
            if not is_acked:
                with col_ack:
                    if st.button(f"Acknowledge #{event_id}", key=f"ack_btn_{event_id}", type="primary"):
                        success, _, err = api_client.acknowledge_event(event_id, acknowledged_by=operator_name)
                        if success:
                            st.toast(f"Alarm #{event_id} acknowledged by {operator_name}!", icon="✅")
                            st.rerun()
                        else:
                            st.error(f"Failed to acknowledge: {err}")
            else:
                with col_ack:
                    st.caption(f"Acknowledged by {ev.get('acknowledged_by', 'Operator')}")
