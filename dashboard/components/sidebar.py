"""
Sidebar Navigation and Control Panel for SHADOW THERMOGUARD AI.
Manages backend connection status, edge device selection, and telemetry refresh cycles.
"""

import time
import streamlit as st
from datetime import datetime
from dashboard.api_client import BackendAPIClient
from dashboard.config import config


def render_sidebar(api_client: BackendAPIClient):
    """
    Renders sidebar controls and returns configuration state:
    (backend_url, selected_device_id, auto_refresh, refresh_interval)
    """
    st.sidebar.markdown(
        """
        <div style="text-align: center; padding-bottom: 1rem;">
            <h2 style="color: #00f0ff; margin-bottom: 0.2rem; font-weight: 800; letter-spacing: -0.02em;">SHADOW</h2>
            <h4 style="color: #94a3b8; margin: 0; font-weight: 600;">THERMOGUARD AI</h4>
            <span style="font-size: 0.75rem; color: #64748b; text-transform: uppercase;">Edge Thermal Intelligence</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.sidebar.divider()

    # 1. Backend Connectivity Controls
    st.sidebar.subheader("🔌 Backend Gateway")
    backend_url = st.sidebar.text_input(
        "FastAPI Base URL",
        value=st.session_state.get("backend_url", config.DEFAULT_BACKEND_URL),
        help="Target address of the existing FastAPI REST server."
    )
    if backend_url != api_client.base_url:
        api_client.update_base_url(backend_url)
        st.session_state["backend_url"] = backend_url

    # Ping health endpoint
    is_healthy, health_data, health_err = api_client.get_health()

    if is_healthy and health_data:
        st.sidebar.markdown(
            """
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 0.5rem;">
                <div style="width: 10px; height: 10px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981;"></div>
                <span style="color: #10b981; font-weight: 600; font-size: 0.85rem;">GATEWAY CONNECTED</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.sidebar.caption(
            f"API v{health_data.get('version', '1.0.0')} | DB: {'Connected' if health_data.get('database_connected') else 'Error'}"
        )
    else:
        st.sidebar.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 0.5rem;">
                <div style="width: 10px; height: 10px; border-radius: 50%; background: #ef4444; box-shadow: 0 0 8px #ef4444;"></div>
                <span style="color: #ef4444; font-weight: 600; font-size: 0.85rem;">BACKEND OFFLINE</span>
            </div>
            <div style="font-size: 0.75rem; color: #f87171; margin-bottom: 0.5rem;">{health_err or 'Unreachable'}</div>
            """,
            unsafe_allow_html=True
        )

    st.sidebar.divider()

    # 2. Edge Device Selector
    st.sidebar.subheader("📡 Edge Device Selector")
    devices = []
    if is_healthy:
        success, dev_list, _ = api_client.get_devices()
        if success and dev_list:
            devices = [d["device_id"] for d in dev_list]

    if devices:
        current_idx = 0
        saved_id = st.session_state.get("selected_device_id")
        if saved_id in devices:
            current_idx = devices.index(saved_id)
        selected_device = st.sidebar.selectbox("Active Device", devices, index=current_idx)
    else:
        selected_device = st.sidebar.text_input(
            "Device Identifier",
            value=st.session_state.get("selected_device_id", config.DEFAULT_DEVICE_ID),
            help="Enter ESP32 Device ID (e.g. ESP32-DEV-001 or SIM-ESP32-001)"
        )

    st.session_state["selected_device_id"] = selected_device

    st.sidebar.divider()

    # 3. Telemetry Stream Controls
    st.sidebar.subheader("⏱️ Telemetry Controls")
    auto_refresh = st.sidebar.toggle("Live Telemetry Stream", value=True)
    refresh_interval = st.sidebar.slider(
        "Polling Rate (sec)",
        min_value=config.MIN_REFRESH_INTERVAL,
        max_value=config.MAX_REFRESH_INTERVAL,
        value=config.DEFAULT_REFRESH_INTERVAL
    )

    if st.sidebar.button("🔄 Poll Now", use_container_width=True):
        st.rerun()

    # Last poll timestamp
    now_str = datetime.now().strftime("%H:%M:%S")
    st.sidebar.caption(f"Last Poll Attempt: `{now_str}`")

    st.sidebar.divider()
    st.sidebar.markdown(
        """
        <div style="font-size: 0.7rem; color: #64748b; line-height: 1.4;">
            <b>Dual-Bank Architecture:</b><br/>
            - Bank A (S1–S8): GPIO34<br/>
            - Bank B (S9–S16): GPIO35<br/>
            - Edge ML: Extra Trees (300 Trees)
        </div>
        """,
        unsafe_allow_html=True
    )

    return backend_url, selected_device, auto_refresh, refresh_interval
