#include "feature_extractor.h"
const char* const FEATURE_NAMES[FEATURE_COUNT] = {
    "mean_temperature",
    "max_temperature",
    "min_temperature",
    "spatial_range",
    "spatial_std",
    "max_sensor_mean",
    "min_sensor_mean",
    "mean_rate_of_change",
    "max_rate_of_change",
    "min_rate_of_change",
    "temporal_std",
    "overall_temperature_rise",
    "most_stable_sensor_std",
    "noisiest_sensor_std",
    "sensor_variation_range",
    "stuck_sensor_count"
};

// Calculate population standard deviation (NumPy ddof=0)
static float calculateStdDev(const float* values, int count) {
    if (count <= 0) {
        return 0.0f;
    }

    double sum = 0.0;

    for (int i = 0; i < count; i++) {
        sum += values[i];
    }

    double mean = sum / count;
    double squaredSum = 0.0;

    for (int i = 0; i < count; i++) {
        double difference = values[i] - mean;
        squaredSum += difference * difference;
    }

    return sqrt(squaredSum / count);
}


// Extract all 16 thermal features
bool extractFeatures(
    const TemperatureWindow& window,
    ThermalFeatures& features
) {

    // Validate input readings
    for (int t = 0; t < WINDOW_SIZE; t++) {
        for (int s = 0; s < SENSOR_COUNT; s++) {
            if (!isfinite(window.readings[t][s])) {
                return false;
            }
        }
    }

    double totalSum = 0.0;

    float maximumTemperature = -INFINITY;
    float minimumTemperature = INFINITY;

    double spatialStdSum = 0.0;

    double sensorSums[SENSOR_COUNT] = {0};

    // ------------------------------------------------
    // 1. SPATIAL FEATURES
    // ------------------------------------------------

    for (int t = 0; t < WINDOW_SIZE; t++) {

        float row[SENSOR_COUNT];

        for (int s = 0; s < SENSOR_COUNT; s++) {

            float temperature = window.readings[t][s];

            row[s] = temperature;

            totalSum += temperature;
            sensorSums[s] += temperature;

            if (temperature > maximumTemperature) {
                maximumTemperature = temperature;
            }

            if (temperature < minimumTemperature) {
                minimumTemperature = temperature;
            }
        }

        spatialStdSum += calculateStdDev(row, SENSOR_COUNT);
    }

    float meanTemperature =
        totalSum / (WINDOW_SIZE * SENSOR_COUNT);

    float spatialRange =
        maximumTemperature - minimumTemperature;

    float spatialStd =
        spatialStdSum / WINDOW_SIZE;

    // Calculate individual sensor means
    float maximumSensorMean = -INFINITY;
    float minimumSensorMean = INFINITY;

    for (int s = 0; s < SENSOR_COUNT; s++) {

        float sensorMean =
            sensorSums[s] / WINDOW_SIZE;

        if (sensorMean > maximumSensorMean) {
            maximumSensorMean = sensorMean;
        }

        if (sensorMean < minimumSensorMean) {
            minimumSensorMean = sensorMean;
        }
    }

    // ------------------------------------------------
    // 2. TEMPORAL FEATURES
    // ------------------------------------------------

    double changeSum = 0.0;

    float maximumChange = -INFINITY;
    float minimumChange = INFINITY;

    int changeCount = (WINDOW_SIZE - 1) * SENSOR_COUNT;

    for (int t = 1; t < WINDOW_SIZE; t++) {

        for (int s = 0; s < SENSOR_COUNT; s++) {

            float change =
                window.readings[t][s]
                - window.readings[t - 1][s];

            changeSum += change;

            if (change > maximumChange) {
                maximumChange = change;
            }

            if (change < minimumChange) {
                minimumChange = change;
            }
        }
    }

    float meanRateOfChange =
        changeSum / changeCount;

    float temporalStdSum = 0.0;

    float sensorVariations[SENSOR_COUNT];

    for (int s = 0; s < SENSOR_COUNT; s++) {

        float sensorReadings[WINDOW_SIZE];

        for (int t = 0; t < WINDOW_SIZE; t++) {
            sensorReadings[t] = window.readings[t][s];
        }

        sensorVariations[s] =
            calculateStdDev(sensorReadings, WINDOW_SIZE);

        temporalStdSum += sensorVariations[s];
    }

    float temporalStd =
        temporalStdSum / SENSOR_COUNT;

    // Average temperature rise between first and last timestep
    double firstRowSum = 0.0;
    double lastRowSum = 0.0;

    for (int s = 0; s < SENSOR_COUNT; s++) {

        firstRowSum += window.readings[0][s];

        lastRowSum +=
            window.readings[WINDOW_SIZE - 1][s];
    }

    float overallTemperatureRise =
        (lastRowSum / SENSOR_COUNT)
        - (firstRowSum / SENSOR_COUNT);

    // ------------------------------------------------
    // 3. SENSOR HEALTH FEATURES
    // ------------------------------------------------

    float mostStableSensorStd = INFINITY;
    float noisiestSensorStd = -INFINITY;

    for (int s = 0; s < SENSOR_COUNT; s++) {

        if (sensorVariations[s] < mostStableSensorStd) {
            mostStableSensorStd = sensorVariations[s];
        }

        if (sensorVariations[s] > noisiestSensorStd) {
            noisiestSensorStd = sensorVariations[s];
        }
    }

    float sensorVariationRange =
        noisiestSensorStd - mostStableSensorStd;

    // Detect stuck sensors using the second half of the window
    int stuckSensorCount = 0;

    const int secondHalfStart = WINDOW_SIZE / 2;

    for (int s = 0; s < SENSOR_COUNT; s++) {

        float secondHalfReadings[
            WINDOW_SIZE - secondHalfStart
        ];

        int index = 0;

        for (int t = secondHalfStart; t < WINDOW_SIZE; t++) {

            secondHalfReadings[index++] =
                window.readings[t][s];
        }

        float secondHalfStd = calculateStdDev(
            secondHalfReadings,
            WINDOW_SIZE - secondHalfStart
        );

        if (secondHalfStd < 0.001f) {
            stuckSensorCount++;
        }
    }

    // ------------------------------------------------
    // 4. STORE FEATURES IN EXACT MODEL ORDER
    // ------------------------------------------------

    features.values[0] = meanTemperature;
    features.values[1] = maximumTemperature;
    features.values[2] = minimumTemperature;
    features.values[3] = spatialRange;
    features.values[4] = spatialStd;
    features.values[5] = maximumSensorMean;
    features.values[6] = minimumSensorMean;
    features.values[7] = meanRateOfChange;
    features.values[8] = maximumChange;
    features.values[9] = minimumChange;
    features.values[10] = temporalStd;
    features.values[11] = overallTemperatureRise;
    features.values[12] = mostStableSensorStd;
    features.values[13] = noisiestSensorStd;
    features.values[14] = sensorVariationRange;
    features.values[15] = stuckSensorCount;

    return true;
}
