#include "thermal_controller.h"
#include <math.h>

ThermalController::ThermalController() {
}

bool ThermalController::processTemperatureReading(
    const float temperatures[SENSOR_COUNT],
    ThermalPrediction& prediction
) {

    // Validate all 16 sensor readings before storing them.
    for (int i = 0; i < SENSOR_COUNT; i++) {
        if (!isfinite(temperatures[i])) {
            return false;
        }
    }

    // Store only valid readings.
    temperatureBuffer.addReading(temperatures);

    // Wait until the 60-reading window is full.
    if (!temperatureBuffer.isReady()) {
        return false;
    }

    // Extract the 16 model features.
    ThermalFeatures features;

    if (!extractFeatures(
            temperatureBuffer.getWindow(),
            features
        )) {
        return false;
    }

    // Run Extra Trees inference.
    if (!predictThermalClass(features, prediction)) {
        return false;
    }

    return true;
}

bool ThermalController::isReady() const {
    return temperatureBuffer.isReady();
}

int ThermalController::getSampleCount() const {
    return temperatureBuffer.getSampleCount();
}