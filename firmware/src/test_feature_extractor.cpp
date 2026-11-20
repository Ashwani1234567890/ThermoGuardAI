
#include <iostream>
#include "feature_extractor.h"

int main() {

    TemperatureWindow window;
    ThermalFeatures features;

    // Generate deterministic test temperatures
    for (int t = 0; t < WINDOW_SIZE; t++) {

        for (int s = 0; s < SENSOR_COUNT; s++) {

            window.readings[t][s] =
                25.0f
                + (s * 0.5f)
                + (t * 0.1f);
        }
    }

    // Make sensor 5 stuck during the second half
    for (int t = 30; t < WINDOW_SIZE; t++) {
        window.readings[t][4] =
            window.readings[29][4];
    }

    // Run feature extraction
    bool success = extractFeatures(window, features);

    if (!success) {
        std::cout << "Feature extraction failed!\n";
        return 1;
    }

    // Print all 16 features
    std::cout << "C++ FEATURE EXTRACTION RESULTS\n";
    std::cout << "================================\n";

    for (int i = 0; i < FEATURE_COUNT; i++) {

        std::cout
            << FEATURE_NAMES[i]
            << " = "
            << features.values[i]
            << "\n";
    }

    return 0;
}
