
import numpy as np

SENSOR_COUNT = 16
WINDOW_SIZE = 60

# Generate the exact same test data as the C++ program
temperatures = np.zeros((WINDOW_SIZE, SENSOR_COUNT))

for t in range(WINDOW_SIZE):
    for s in range(SENSOR_COUNT):
        temperatures[t, s] = 25.0 + (s * 0.5) + (t * 0.1)

# Freeze sensor index 4 from timestep 30 onwards
temperatures[30:, 4] = temperatures[29, 4]

features = {}

# SPATIAL FEATURES
features["mean_temperature"] = np.mean(temperatures)
features["max_temperature"] = np.max(temperatures)
features["min_temperature"] = np.min(temperatures)

features["spatial_range"] = (
    features["max_temperature"] - features["min_temperature"]
)

features["spatial_std"] = np.mean(
    np.std(temperatures, axis=1)
)

features["max_sensor_mean"] = np.max(
    np.mean(temperatures, axis=0)
)

features["min_sensor_mean"] = np.min(
    np.mean(temperatures, axis=0)
)

# TEMPORAL FEATURES
temperature_changes = np.diff(temperatures, axis=0)

features["mean_rate_of_change"] = np.mean(temperature_changes)
features["max_rate_of_change"] = np.max(temperature_changes)
features["min_rate_of_change"] = np.min(temperature_changes)

features["temporal_std"] = np.mean(
    np.std(temperatures, axis=0)
)

features["overall_temperature_rise"] = (
    np.mean(temperatures[-1]) -
    np.mean(temperatures[0])
)

# SENSOR HEALTH FEATURES
sensor_variations = np.std(temperatures, axis=0)

features["most_stable_sensor_std"] = np.min(sensor_variations)
features["noisiest_sensor_std"] = np.max(sensor_variations)

features["sensor_variation_range"] = (
    np.max(sensor_variations) -
    np.min(sensor_variations)
)

second_half = temperatures[WINDOW_SIZE // 2:]
second_half_variations = np.std(second_half, axis=0)

features["stuck_sensor_count"] = np.sum(
    second_half_variations < 0.001
)

# DISPLAY RESULTS
print("\nPYTHON FEATURE EXTRACTION RESULTS")
print("=" * 45)

for name, value in features.items():
    print(f"{name} = {value}")
