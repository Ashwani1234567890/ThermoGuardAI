
import numpy as np
import pandas as pd
from pathlib import Path

# ---------------------------------
# VALIDATION CONFIGURATION
# ---------------------------------

np.random.seed(2026)

SENSORS = 16
READINGS_PER_SCENARIO = 60
SCENARIOS_PER_CLASS = 100

sensor_columns = [
    f"ntc_{i:02d}" for i in range(1, SENSORS + 1)
]

records = []

# ---------------------------------
# GENERATE ONE VALIDATION SCENARIO
# ---------------------------------

def generate_validation_scenario(label, scenario_number):

    scenario_id = f"validation_{label}_{scenario_number:03d}"

    # Wider ambient temperature range than training
    ambient = np.random.uniform(18, 40)

    # More variation between physical sensors
    sensor_offsets = np.random.normal(0, 0.6, SENSORS)

    # Increased sensor noise
    noise_level = np.random.uniform(0.20, 0.60)

    hotspot_sensor = np.random.randint(0, SENSORS)

    # Vary anomaly and heating intensity
    hotspot_intensity = np.random.uniform(7, 18)
    gradual_intensity = np.random.uniform(10, 24)
    rapid_intensity = np.random.uniform(20, 45)
    spike_intensity = np.random.uniform(20, 55)
    stuck_temperature = np.random.uniform(65, 100)

    # Randomize the time at which heating starts
    rapid_start = np.random.randint(5, 20)
    anomaly_start = np.random.randint(10, 25)

    # Randomize anomaly subtype
    anomaly_type = scenario_number % 3

    for timestep in range(READINGS_PER_SCENARIO):

        temperatures = (
            ambient
            + sensor_offsets
            + np.random.normal(0, noise_level, SENSORS)
        )

        # 1. NORMAL
        if label == "normal":
            pass

        # 2. HOTSPOT
        elif label == "hotspot":

            temperatures[hotspot_sensor] += hotspot_intensity

            row = hotspot_sensor // 4
            col = hotspot_sensor % 4

            for i in range(SENSORS):
                r = i // 4
                c = i % 4

                distance = abs(row - r) + abs(col - c)

                if distance == 1:
                    temperatures[i] += hotspot_intensity * 0.25

        # 3. GRADUAL HEATING
        elif label == "gradual_heating":

            heating = (
                timestep / (READINGS_PER_SCENARIO - 1)
            ) * gradual_intensity

            temperatures[hotspot_sensor] += heating

            for i in range(SENSORS):
                if i != hotspot_sensor:
                    temperatures[i] += heating * 0.15

        # 4. RAPID RISE
        elif label == "rapid_rise":

            if timestep >= rapid_start:

                rise = min(
                    (timestep - rapid_start + 1) * 2.2,
                    rapid_intensity
                )

                temperatures[hotspot_sensor] += rise

                row = hotspot_sensor // 4
                col = hotspot_sensor % 4

                for i in range(SENSORS):

                    r = i // 4
                    c = i % 4

                    if abs(row - r) + abs(col - c) == 1:
                        temperatures[i] += rise * 0.18

        # 5. SENSOR ANOMALY
        elif label == "sensor_anomaly":

            if timestep >= anomaly_start:

                if anomaly_type == 0:

                    # Stuck sensor at a variable value
                    temperatures[hotspot_sensor] = stuck_temperature

                elif anomaly_type == 1:

                    # Sudden spike with variable magnitude
                    temperatures[hotspot_sensor] += spike_intensity

                else:

                    # High-noise sensor
                    temperatures[hotspot_sensor] += np.random.normal(
                        0, np.random.uniform(8, 18)
                    )

        # Keep readings in simulation range
        temperatures = np.clip(temperatures, -10, 120)

        record = {
            "scenario_id": scenario_id,
            "timestep": timestep,
            "ambient_temp": round(float(ambient), 2),
            "label": label
        }

        for i, sensor in enumerate(sensor_columns):
            record[sensor] = round(float(temperatures[i]), 2)

        records.append(record)


# ---------------------------------
# GENERATE ALL FIVE CLASSES
# ---------------------------------

classes = [
    "normal",
    "hotspot",
    "gradual_heating",
    "rapid_rise",
    "sensor_anomaly"
]

for label in classes:

    print(f"Generating validation {label} scenarios...")

    for scenario_number in range(SCENARIOS_PER_CLASS):

        generate_validation_scenario(
            label,
            scenario_number
        )


# ---------------------------------
# CREATE VALIDATION DATASET
# ---------------------------------

df = pd.DataFrame(records)

OUTPUT_PATH = Path(
    "data/simulated/thermal_validation_dataset.csv"
)

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)

df.to_csv(OUTPUT_PATH, index=False)

# ---------------------------------
# VALIDATION SUMMARY
# ---------------------------------

print("\nVALIDATION DATASET GENERATED")

print("Dataset shape:", df.shape)

print("\nClass distribution:")
print(df["label"].value_counts())

print("\nMissing values:", df.isnull().sum().sum())

print("\nSaved location:")
print(OUTPUT_PATH)
