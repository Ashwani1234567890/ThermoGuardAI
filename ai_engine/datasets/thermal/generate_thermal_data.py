
import numpy as np
import pandas as pd
from pathlib import Path

# Reproducible random data
np.random.seed(42)

# Project paths
OUTPUT_PATH = Path("data/simulated/thermal_sensor_dataset.csv")

# Dataset configuration
SENSORS = 16
SCENARIOS_PER_CLASS = 100
READINGS_PER_SCENARIO = 60

sensor_columns = [
    f"ntc_{i:02d}" for i in range(1, SENSORS + 1)
]

records = []

def generate_scenario(label, scenario_number):

    scenario_id = f"{label}_{scenario_number:03d}"

    # Ambient temperature for this scenario
    ambient = np.random.uniform(25, 32)

    # Small differences between physical sensors
    sensor_offsets = np.random.normal(0, 0.3, SENSORS)

    # Select a location in the 4x4 sensor grid
    hotspot_sensor = np.random.randint(0, SENSORS)

    for timestep in range(READINGS_PER_SCENARIO):

        # Normal temperature readings
        temperatures = (
            ambient
            + sensor_offsets
            + np.random.normal(0, 0.15, SENSORS)
        )

        # 1. NORMAL
        if label == "normal":
            pass

        # 2. HOTSPOT
        elif label == "hotspot":

            # Persistent localized high temperature
            temperatures[hotspot_sensor] += 12

            # Slight effect on neighboring sensors
            row = hotspot_sensor // 4
            col = hotspot_sensor % 4

            for i in range(SENSORS):
                r = i // 4
                c = i % 4

                distance = abs(row - r) + abs(col - c)

                if distance == 1:
                    temperatures[i] += 3

        # 3. GRADUAL HEATING
        elif label == "gradual_heating":

            # Temperature rises progressively
            heating = (timestep / READINGS_PER_SCENARIO) * 15

            temperatures[hotspot_sensor] += heating

            # Nearby sensors experience a smaller increase
            for i in range(SENSORS):
                if i != hotspot_sensor:
                    temperatures[i] += heating * 0.12

        # 4. RAPID RISE
        elif label == "rapid_rise":

            # Sudden temperature increase after 10 readings
            if timestep >= 10:
                rise = min((timestep - 9) * 1.8, 35)

                temperatures[hotspot_sensor] += rise

                # Heat spreads to adjacent sensors
                row = hotspot_sensor // 4
                col = hotspot_sensor % 4

                for i in range(SENSORS):
                    r = i // 4
                    c = i % 4

                    if abs(row - r) + abs(col - c) == 1:
                        temperatures[i] += rise * 0.15

        # 5. SENSOR ANOMALY
        elif label == "sensor_anomaly":

            # One sensor develops an abnormal reading
            if timestep >= 15:
                anomaly_type = scenario_number % 3

                if anomaly_type == 0:
                    # Sensor gets stuck at a fixed value
                    temperatures[hotspot_sensor] = 85.0

                elif anomaly_type == 1:
                    # Sensor suddenly reports an extreme value
                    temperatures[hotspot_sensor] += 40

                else:
                    # Sensor produces unusually noisy readings
                    temperatures[hotspot_sensor] += np.random.normal(
                        0, 12
                    )

        # Keep readings within a plausible simulation range
        temperatures = np.clip(temperatures, -10, 120)

        record = {
            "scenario_id": scenario_id,
            "timestep": timestep,
            "ambient_temp": round(ambient, 2),
            "label": label
        }

        for i, sensor in enumerate(sensor_columns):
            record[sensor] = round(float(temperatures[i]), 2)

        records.append(record)


# Generate all five classes
classes = [
    "normal",
    "hotspot",
    "gradual_heating",
    "rapid_rise",
    "sensor_anomaly"
]

for label in classes:

    print(f"Generating {label} scenarios...")

    for scenario_number in range(SCENARIOS_PER_CLASS):
        generate_scenario(label, scenario_number)


# Convert records into a DataFrame
df = pd.DataFrame(records)

# Create output directory if required
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# Save dataset
df.to_csv(OUTPUT_PATH, index=False)

# Display dataset information
print("\nTHERMAL DATASET GENERATED SUCCESSFULLY")

print("\nDataset shape:")
print(df.shape)

print("\nClass distribution:")
print(df["label"].value_counts())

print("\nSensor columns:")
print(sensor_columns)

print("\nSaved location:")
print(OUTPUT_PATH)
