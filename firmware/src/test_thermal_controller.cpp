#include <iostream>
#include <cmath>
#include <limits>
#include "thermal_controller.h"

int main() {

    ThermalController controller;

    float temperatures[SENSOR_COUNT];
    ThermalPrediction prediction;

    std::cout << "INVALID INPUT AND RECOVERY TEST\n";
    std::cout << "================================\n";

    // Fill the initial window with valid readings.
    for (int t = 0; t < WINDOW_SIZE; t++) {
        for (int s = 0; s < SENSOR_COUNT; s++) {
            temperatures[s] = 28.0f;
        }

        controller.processTemperatureReading(
            temperatures, prediction
        );
    }

    std::cout << "Initial window ready: "
              << controller.isReady() << '\n';

    // Inject a NaN value.
    for (int s = 0; s < SENSOR_COUNT; s++) {
        temperatures[s] = 28.0f;
    }

    temperatures[5] =
        std::numeric_limits<float>::quiet_NaN();

    bool invalidResult =
        controller.processTemperatureReading(
            temperatures, prediction
        );

    std::cout << "Prediction with NaN: "
              << (invalidResult ? "GENERATED" : "REJECTED")
              << '\n';

    // Feed 60 fresh valid readings.
    bool recoveryResult = false;

    for (int t = 0; t < WINDOW_SIZE; t++) {
        for (int s = 0; s < SENSOR_COUNT; s++) {
            temperatures[s] = 28.0f;
        }

        recoveryResult =
            controller.processTemperatureReading(
                temperatures, prediction
            );
    }

    std::cout << "Prediction after recovery: "
              << (recoveryResult ? "GENERATED" : "FAILED")
              << '\n';

    if (!invalidResult && recoveryResult) {
        std::cout << "TEST PASSED\n";
    } else {
        std::cout << "TEST FAILED\n";
    }

    return 0;
}