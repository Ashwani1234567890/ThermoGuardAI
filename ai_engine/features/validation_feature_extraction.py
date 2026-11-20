
import pandas as pd
import numpy as np
from pathlib import Path

# Project paths
INPUT_PATH = Path("data/simulated/thermal_validation_dataset.csv")
OUTPUT_PATH = Path("data/processed/thermal_validation_features.csv")

# Sensor configuration
SENSOR_COLUMNS = [f"ntc_{i:02d}" for i in range(1, 17)]

# Load simulated sensor data
df = pd.read_csv(INPUT_PATH)

feature_records = []


def extract_scenario_features(group):

    group = group.sort_values("timestep")
    temperatures = group[SENSOR_COLUMNS].to_numpy(dtype=float)

    row_features = {}

    # -------------------------------
    # SPATIAL FEATURES
    # -------------------------------

    row_features["mean_temperature"] = np.mean(temperatures)
    row_features["max_temperature"] = np.max(temperatures)
    row_features["min_temperature"] = np.min(temperatures)

    row_features["spatial_range"] = (
        row_features["max_temperature"]
        - row_features["min_temperature"]
    )

    row_features["spatial_std"] = np.mean(
        np.std(temperatures, axis=1)
    )

    row_features["max_sensor_mean"] = np.max(
        np.mean(temperatures, axis=0)
    )

    row_features["min_sensor_mean"] = np.min(
        np.mean(temperatures, axis=0)
    )

    # -------------------------------
    # TEMPORAL FEATURES
    # -------------------------------

    temperature_changes = np.diff(temperatures, axis=0)

    row_features["mean_rate_of_change"] = np.mean(
        temperature_changes
    )

    row_features["max_rate_of_change"] = np.max(
        temperature_changes
    )

    row_features["min_rate_of_change"] = np.min(
        temperature_changes
    )

    row_features["temporal_std"] = np.mean(
        np.std(temperatures, axis=0)
    )

    row_features["overall_temperature_rise"] = (
        np.mean(temperatures[-1])
        - np.mean(temperatures[0])
    )

    # -------------------------------
    # SENSOR HEALTH FEATURES
    # -------------------------------

    sensor_variations = np.std(temperatures, axis=0)

    row_features["most_stable_sensor_std"] = np.min(
        sensor_variations
    )

    row_features["noisiest_sensor_std"] = np.max(
        sensor_variations
    )

    row_features["sensor_variation_range"] = (
        np.max(sensor_variations)
        - np.min(sensor_variations)
    )

    # Detect sensors that become stuck
    second_half = temperatures[len(temperatures) // 2:]

    second_half_variations = np.std(
        second_half, axis=0
    )

    row_features["stuck_sensor_count"] = np.sum(
        second_half_variations < 0.001
    )

    # -------------------------------
    # SCENARIO INFORMATION
    # -------------------------------

    row_features["scenario_id"] = (
        group["scenario_id"].iloc[0]
    )

    row_features["label"] = (
        group["label"].iloc[0]
    )

    return row_features


# Extract features scenario by scenario
for scenario_id, group in df.groupby("scenario_id"):

    features = extract_scenario_features(group)

    feature_records.append(features)


# Create feature DataFrame
feature_df = pd.DataFrame(feature_records)

# Create output directory
OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)

# Save feature dataset
feature_df.to_csv(
    OUTPUT_PATH,
    index=False
)

# -------------------------------
# DISPLAY RESULTS
# -------------------------------

print("\nFEATURE EXTRACTION COMPLETED")

print("\nDataset shape:")
print(feature_df.shape)

print("\nClass distribution:")
print(feature_df["label"].value_counts())

print("\nFeature columns:")
print(feature_df.columns.tolist())

print("\nMissing values:")
print(feature_df.isnull().sum().sum())

print("\nStuck sensor count by class:")
print(
    feature_df.groupby("label")["stuck_sensor_count"]
    .mean()
    .round(2)
)

print("\nFirst five records:")
print(feature_df.head())

print("\nSaved location:")
print(OUTPUT_PATH)
