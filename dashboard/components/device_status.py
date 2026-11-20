"""
Edge Device & System Health Component for SHADOW THERMOGUARD AI.
Presents verified device telemetry health without fabricating physical hardware states.
"""

import streamlit as st
from typing import Dict, Any, Optional


def render_device_status_banner(device_status: Optional[Dict[str, Any]], device_id: str):
    """
    Renders device online/offline banner based on existing GET /api/devices/{device_id}/status.
    """
    if not device_status:
        st.markdown(
            f"""
            <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 0.75rem 1rem; color: #f87171; display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <b>DEVICE NOT FOUND:</b> <code>{device_id}</code> is not registered on the backend gateway.
                </div>
                <span class="status-pill pill-offline">OFFLINE</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    is_online = device_status.get("is_online", False)
    sec_diff = device_status.get("seconds_since_last_seen", 0.0)
    fw_ver = device_status.get("firmware_version", "1.0.0")
    boot_count = device_status.get("boot_count", 0)
    last_seen = device_status.get("last_seen", "N/A")

    status_pill = (
        '<span class="status-pill pill-online">🟢 ONLINE</span>'
        if is_online else
        '<span class="status-pill pill-offline">🔴 OFFLINE</span>'
    )

    st.markdown(
        f"""
        <div style="background: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 0.75rem 1.25rem; margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-weight: 700; color: #f8fafc; font-size: 1.05rem;">{device_id}</span>
                    {status_pill}
                    <span style="font-size: 0.8rem; color: #94a3b8;">FW: v{fw_ver}</span>
                    <span style="font-size: 0.8rem; color: #94a3b8;">Reboot Count: {boot_count}</span>
                </div>
                <div style="font-size: 0.8rem; color: #64748b;">
                    Last Ping: <b>{sec_diff:.1f}s ago</b> ({last_seen})
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
