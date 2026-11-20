import streamlit as st

import time
from collections import defaultdict, deque

import pandas as pd
import requests
import streamlit as st

# ---------------- CONFIGURATION ----------------

st.set_page_config(
    page_title="ThermoGuard AI",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp {
        background: #0b1120;
        color: #e5edf7;
    }
    [data-testid="stMetric"] {
        background: #151f32;
        border: 1px solid #263750;
        padding: 18px;
        border-radius: 12px;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #263750;
        border-radius: 10px;
    }
    h1, h2, h3 {
        color: #e5edf7;
    }
    .subtitle {
        color: #94a3b8;
        font-size: 14px;
    }
    .normal {
        color: #4ade80;
        font-weight: bold;
    }
    .warning {
        color: #facc15;
        font-weight: bold;
    }
    .critical {
        color: #f87171;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# ---------------- SESSION STATE ----------------

if "history" not in st.session_state:
    st.session_state.history = defaultdict(
        lambda: deque(maxlen=300)
    )

if "api_url" not in st.session_state:
    st.session_state.api_url = "http://127.0.0.1:8080/api/status"


# ---------------- SIDEBAR ----------------

with st.sidebar:
    st.title("🌡️ ThermoGuard AI")
    st.caption("Decentralized Thermal Monitoring")

    st.divider()

    st.subheader("Connection")

    api_url = st.text_input(
        "Backend API URL",
        value=st.session_state.api_url
    )

    st.session_state.api_url = api_url

    st.caption("Default: localhost:8080/api/status")

    st.divider()

    st.subheader("System Information")
    st.write("**Protocol:** UDP")
    st.write("**Transport:** Wi-Fi")
    st.write("**Receiver port:** 5005")
    st.write("**Sensor array:** 4 × 4")
    st.write("**Polling:** 1 second")

    st.divider()

    st.caption(
        "Prototype monitoring interface. "
        "Not a certified safety controller."
    )


# ---------------- DATA FETCHING ----------------

def fetch_data():
    try:
        response = requests.get(
            st.session_state.api_url,
            timeout=2
        )
        response.raise_for_status()
        return response.json(), None

    except requests.RequestException as error:
        return None, str(error)

    except ValueError as error:
        return None, f"Invalid JSON response: {error}"


# ---------------- HELPER FUNCTIONS ----------------

def classify_state(node):
    if node.get("stale"):
        return "OFFLINE"

    return node.get("state", "UNKNOWN")


def get_state_color(state):
    colors = {
        "NORMAL": "#4ade80",
        "WARNING": "#facc15",
        "CRITICAL": "#f87171",
        "SENSOR_FAULT": "#c084fc",
        "OFFLINE": "#94a3b8"
    }
    return colors.get(state, "#94a3b8")


def temperature(value):
    if value is None:
        return "Unavailable"
    return f"{value:.2f} °C"


# ---------------- MAIN DASHBOARD ----------------

@st.fragment(run_every="300s")
def dashboard():

    data, error = fetch_data()

    # Header
    col1, col2 = st.columns([3, 1])

    with col1:
        st.title("Edge Thermal Network")
        st.markdown(
            '<p class="subtitle">'
            'Real-time thermal threat detection and '
            'distributed sensor monitoring'
            '</p>',
            unsafe_allow_html=True
        )

    with col2:
        st.caption("LIVE MONITORING")
        if error:
            st.error("Receiver disconnected")
        else:
            st.success("Receiver connected")

    st.divider()

    if error:
        st.error(f"Backend connection failed: {error}")
        st.info(
            "Start thermal_dashboard.py and verify the API URL."
        )
        return

    nodes = (data or {}).get("nodes", [])
    counters = (data or {}).get("counters", {})
    events = (data or {}).get("events", [])

    # Determine node states
    total_nodes = len(nodes)

    online_nodes = [
        n for n in nodes if not n.get("stale", True)
    ]

    critical_nodes = [
        n for n in online_nodes
        if n.get("status_code") == 2
    ]

    warning_nodes = [
        n for n in online_nodes
        if n.get("status_code") == 1
    ]

    fault_nodes = [
        n for n in online_nodes
        if n.get("status_code") == 3
    ]

    offline_nodes = [
        n for n in nodes if n.get("stale", False)
    ]

    valid_temps = [
        n["max_temp_c"]
        for n in online_nodes
        if n.get("max_temp_c") is not None
    ]

    maximum_temp = max(valid_temps) if valid_temps else None

    highest_threat = max(
        [n.get("threat_score", 0) for n in online_nodes],
        default=0
    )

    # ---------------- METRICS ----------------

    st.subheader("Network Overview")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Total Nodes", total_nodes)
    c2.metric("Online", len(online_nodes))
    c3.metric("Critical", len(critical_nodes))
    c4.metric("Warnings", len(warning_nodes))
    c5.metric(
        "Maximum Temperature",
        temperature(maximum_temp)
    )

    st.divider()

    # ---------------- ALERTS ----------------

    st.subheader("🚨 Threat Monitoring")

    if critical_nodes:
        for node in critical_nodes:
            st.error(
                f"CRITICAL: Node {node['node_id']} | "
                f"Threat score: {node['threat_score']} | "
                f"Maximum temperature: "
                f"{temperature(node.get('max_temp_c'))}"
            )

    elif fault_nodes:
        for node in fault_nodes:
            st.error(
                f"SENSOR FAULT: Node {node['node_id']}"
            )

    elif warning_nodes:
        for node in warning_nodes:
            st.warning(
                f"WARNING: Node {node['node_id']} | "
                f"Threat score: {node['threat_score']}"
            )

    else:
        st.success("No active thermal alerts.")

    if offline_nodes:
        st.warning(
            f"{len(offline_nodes)} node(s) have stale telemetry."
        )

    st.divider()

    # ---------------- NODE TABLE ----------------

    st.subheader("📡 Sensor Network")

    if nodes:

        rows = []

        for node in nodes:

            state = classify_state(node)

            rows.append({
                "Node ID": node["node_id"],
                "IP Address": node.get("address", "Unknown"),
                "Status": state,
                "Threat Score": node.get("threat_score", 0),
                "Max Temperature": node.get("max_temp_c"),
                "Rise (°C/s)": node.get("rise_c_s"),
                "Hotspot": (
                    str(tuple(node["hotspot"]))
                    if node.get("hotspot") is not None
                    else "Unavailable"
                ),
                "Age (s)": round(node.get("age_s", 0), 2),
                "Sequence Gaps": node.get("sequence_gaps", 0)
            })

        df = pd.DataFrame(rows)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Max Temperature": st.column_config.NumberColumn(
                    format="%.2f °C"
                ),
                "Rise (°C/s)": st.column_config.NumberColumn(
                    format="%.2f"
                ),
                "Threat Score": st.column_config.ProgressColumn(
                    min_value=0,
                    max_value=100,
                    format="%d"
                ),
                "Age (s)": st.column_config.NumberColumn(
                    format="%.2f"
                )
            }
        )

    else:
        st.info("Waiting for telemetry from ESP32 nodes.")

    st.divider()

    # ---------------- NODE DETAILS ----------------

    st.subheader("🔬 Node Analytics")

    if nodes:

        node_ids = [n["node_id"] for n in nodes]

        selected_id = st.selectbox(
            "Select a sensor node",
            node_ids
        )

        selected_node = next(
            n for n in nodes
            if n["node_id"] == selected_id
        )

        a, b, c, d = st.columns(4)

        a.metric(
            "Threat Score",
            selected_node.get("threat_score", 0)
        )

        b.metric(
            "Temperature",
            temperature(selected_node.get("max_temp_c"))
        )

        b2 = selected_node.get("rise_c_s")
        c.metric(
            "Temperature Rise",
            f"{b2:.2f} °C/s" if b2 is not None else "Unavailable"
        )

        d.metric(
            "Sequence Gaps",
            selected_node.get("sequence_gaps", 0)
        )

        st.markdown("**Selected node status**")

        state = classify_state(selected_node)
        color = get_state_color(state)

        st.markdown(
            f'<h3 style="color:{color}">{state}</h3>',
            unsafe_allow_html=True
        )

        # Store observed snapshots in session memory
        if not selected_node.get("stale", True):
            current_temp = selected_node.get("max_temp_c")

            if current_temp is not None:
                st.session_state.history[selected_id].append({
                    "time": time.time(),
                    "temperature": current_temp
                })

        history = list(st.session_state.history[selected_id])

        if history:
            chart_df = pd.DataFrame(history)
            chart_df["time"] = pd.to_datetime(
                chart_df["time"],
                unit="s"
            )
            chart_df = chart_df.set_index("time")

            st.markdown("**Observed temperature history**")

            st.line_chart(
                chart_df[["temperature"]],
                y_label="Temperature (°C)",
                height=280
            )

        else:
            st.info(
                "Temperature history will appear after "
                "the selected node sends valid readings."
            )

        # Hotspot location
        hotspot = selected_node.get("hotspot")

        if hotspot is not None:
            x, y = hotspot
            st.info(
                f"Detected hotspot coordinates: X={x}, Y={y}"
            )

    st.divider()

    # ---------------- COMMUNICATION DIAGNOSTICS ----------------

    st.subheader("⚙️ Communication Diagnostics")

    d1, d2, d3, d4 = st.columns(4)

    d1.metric(
        "Packets Received",
        counters.get("received", 0)
    )

    d2.metric(
        "CRC Errors",
        counters.get("bad_crc", 0)
    )

    d3.metric(
        "Invalid Packets",
        counters.get("invalid", 0)
    )

    d4.metric(
        "Bad Length",
        counters.get("bad_length", 0)
    )

    st.caption(
        f"Online: {len(online_nodes)} | "
        f"Offline: {len(offline_nodes)} | "
        f"Highest threat score: {highest_threat}"
    )

    st.divider()

    # ---------------- EVENT LOG ----------------

    st.subheader("📋 Recent Thermal Events")

    if events:
        for event in reversed(events):
            st.code(event, language=None)
    else:
        st.info("No events recorded yet.")

    st.caption(
        "Telemetry refreshes every second. "
        "Temperature history is session-local and resets "
        "when the Streamlit session is lost."
    )


dashboard()
