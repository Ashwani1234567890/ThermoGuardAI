"""
Page 3: Thermal Threat Alerts and Event Management for SHADOW THERMOGUARD AI.
Allows filtering, inspection, and operator acknowledgment of safety alerts.
"""

import streamlit as st
import pandas as pd
from pathlib import Path

from dashboard.config import config
from dashboard.api_client import BackendAPIClient
from dashboard.components import render_sidebar, render_alerts_section

st.set_page_config(
    page_title=f"{config.APP_NAME} – Alerts & Events",
    page_icon="🚨",
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

st.title("🚨 Thermal Threat Alerts & Events")
st.caption("Active threshold alarms, AI anomaly events, and operator acknowledgment audit trail.")

# Operator Identification
col_op, col_filter = st.columns([3, 7])
with col_op:
    operator_name = st.text_input("Operator Name / ID", value="Lead Safety Engineer")

# Filter Controls
with col_filter:
    c1, c2, c3 = st.columns(3)
    with c1:
        severity_filter = st.selectbox("Severity", ["ALL", "CRITICAL", "WARNING", "FAULT", "NORMAL"])
    with c2:
        ack_filter = st.selectbox("Status", ["ALL", "Unacknowledged Only", "Acknowledged Only"])
    with c3:
        event_limit = st.slider("Max Events", min_value=10, max_value=100, value=30)

# Build query params
sev_param = None if severity_filter == "ALL" else severity_filter
ack_param = None
if ack_filter == "Unacknowledged Only":
    ack_param = False
elif ack_filter == "Acknowledged Only":
    ack_param = True

success, events, err = api_client.get_events(
    device_id=selected_device,
    severity=sev_param,
    acknowledged=ack_param,
    page_size=event_limit
)

# Summary Counters
if success and events is not None:
    total_events = len(events)
    crit_count = sum(1 for e in events if e.get("severity") == "CRITICAL")
    warn_count = sum(1 for e in events if e.get("severity") == "WARNING")
    unack_count = sum(1 for e in events if not e.get("acknowledged"))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Filtered Events", total_events)
    m2.metric("Critical Alarms", crit_count, delta="Immediate Action" if crit_count > 0 else None, delta_color="inverse")
    m3.metric("Warning Alerts", warn_count)
    m4.metric("Pending Acknowledgment", unack_count, delta="Requires Sign-off" if unack_count > 0 else None, delta_color="inverse")

    st.divider()

    # Alert List
    render_alerts_section(api_client, events, operator_name=operator_name)

    st.divider()

    # Raw Event Table Export
    if events:
        st.markdown("#### 📥 Event Log Export")
        df_events = pd.DataFrame(events)
        st.dataframe(df_events, use_container_width=True, hide_index=True)
else:
    st.error(f"Failed to fetch thermal events from backend: {err}")
