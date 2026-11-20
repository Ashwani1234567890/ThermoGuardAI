#ifndef THERMAL_INFERENCE_H
#define THERMAL_INFERENCE_H

#include "feature_extractor.h"

struct ThermalPrediction {
    int class_index;
    float probabilities[5];
    const char* class_name;
    float confidence;
};

bool predictThermalClass(
    const ThermalFeatures& features,
    ThermalPrediction& prediction
);

#endif