
#include "thermal_inference.h"

#include <iostream>
#include <iomanip>

int main() {

    ThermalFeatures features;
    ThermalPrediction prediction;

    std::cout << std::fixed << std::setprecision(8);

    int sample_count = 0;

    // Read multiple samples until input ends.
    while (std::cin >> features.values[0]) {

        bool valid_input = true;

        for (int i = 1; i < FEATURE_COUNT; i++) {
            if (!(std::cin >> features.values[i])) {
                valid_input = false;
                break;
            }
        }

        if (!valid_input) {
            std::cerr << "Invalid input for sample.\n";
            return 1;
        }

        if (!predictThermalClass(features, prediction)) {
            std::cerr << "Prediction failed for sample "
                      << sample_count << "\n";
            return 1;
        }

        std::cout << prediction.class_index;

        for (int i = 0; i < 5; i++) {
            std::cout << " "
                      << prediction.probabilities[i];
        }

        std::cout << "\n";

        sample_count++;
    }

    std::cerr << "Total samples processed: "
              << sample_count << "\n";

    return 0;
}
