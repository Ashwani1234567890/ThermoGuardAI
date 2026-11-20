# THERMOGUARD AI
### Decentralized Edge Intelligence for Real-Time Thermal Threat Detection

SHADOW THERMOGUARD AI is an intelligent IoT-based thermal monitoring and threat detection system designed to identify abnormal temperature patterns, localized hotspots, gradual heating, rapid temperature rises, and sensor anomalies.

The system integrates an ESP32 microcontroller, a 16-sensor NTC thermistor array, deterministic safety logic, and a machine learning-based Extra Trees classifier to enable intelligent thermal monitoring at the edge.

Unlike conventional cloud-dependent monitoring systems, the project emphasizes local processing and edge intelligence, allowing critical thermal safety decisions to operate independently of continuous internet connectivity.

### Key Features

- **16-Sensor Thermal Monitoring:** Monitors temperature variations through a 4×4 NTC thermistor grid.
- **Edge Computing:** Performs local processing and thermal threat assessment using ESP32.
- **AI-Based Classification:** Uses an Extra Trees machine learning model with 300 trees.
- **Five Threat Categories:** Identifies Normal, Hotspot, Gradual Heating, Rapid Rise, and Sensor Anomaly conditions.
- **Deterministic Safety Logic:** Maintains rule-based safety checks independently of AI predictions.
- **Backend Integration:** Uses a backend API for telemetry handling and data management.
- **Interactive Dashboard:** Streamlit-based interface for thermal visualisation, sensor monitoring, and threat analysis.

### Technology Stack

- **Hardware:** ESP32, NTC Thermistors, Multiplexers
- **Embedded Programming:** C++
- **Artificial Intelligence:** Python, Scikit-learn, Extra Trees
- **Backend:** FastAPI
- **Database:** SQLite
- **Frontend:** Streamlit
- **Data Visualisation:** Plotly

### Project Objective

To develop a decentralized, intelligent thermal threat monitoring solution that combines IoT sensing, machine learning, and edge computing to support early detection of potentially hazardous temperature conditions.

### Note

The machine learning model has been evaluated using synthetic thermal scenarios. Its reported validation performance should not be interpreted as verified real-world or industrial safety performance. Physical hardware validation and sensor calibration are necessary before deployment in safety-critical environments.
