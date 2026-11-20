
#include "thermal_inference.h"
#include "thermal_model.h"

#include <math.h>
#include <stdint.h>

bool predictThermalClass(
    const ThermalFeatures& features,
    ThermalPrediction& prediction
) {
    // Confirm that the exported model has five classes.
    if (CLASS_COUNT != 5) {
        return false;
    }

    // Validate all 16 input features.
    for (int i = 0; i < FEATURE_COUNT; i++) {
        if (!isfinite(features.values[i])) {
            return false;
        }
    }

    float probabilities[CLASS_COUNT] = {0.0f};

    // Traverse all 300 decision trees.
    for (int tree_index = 0; tree_index < TREE_COUNT; tree_index++) {

        int node = 0;
        bool leaf_found = false;

        // Prevent an invalid tree from causing an infinite loop.
        for (int step = 0;
             step < TREE_NODE_COUNTS[tree_index];
             step++) {

            int feature_index = TREE_FEATURES[tree_index][node];

            // A feature index of -2 identifies a leaf node.
            if (feature_index == -2) {

                for (int c = 0; c < CLASS_COUNT; c++) {
                    probabilities[c] +=
                        TREE_VALUES[tree_index][node][c];
                }

                leaf_found = true;
                break;
            }

            if (feature_index < 0 || feature_index >= FEATURE_COUNT) {
                return false;
            }

            float feature_value = features.values[feature_index];
            float threshold = TREE_THRESHOLDS[tree_index][node];

            if (feature_value <= threshold) {
                node = TREE_LEFT[tree_index][node];
            } else {
                node = TREE_RIGHT[tree_index][node];
            }

            if (node < 0 ||
                node >= TREE_NODE_COUNTS[tree_index]) {
                return false;
            }
        }

        if (!leaf_found) {
            return false;
        }
    }

    // Average probabilities across all trees.
    int best_class = 0;

    for (int c = 0; c < CLASS_COUNT; c++) {
        probabilities[c] /= TREE_COUNT;

        prediction.probabilities[c] = probabilities[c];

        if (probabilities[c] > probabilities[best_class]) {
            best_class = c;
        }
    }

    prediction.class_index = best_class;
    prediction.class_name = MODEL_CLASSES[best_class];
    prediction.confidence = probabilities[best_class];

    return true;
}
