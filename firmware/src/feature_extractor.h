
#ifndef FEATURE_EXTRACTOR_H
#define FEATURE_EXTRACTOR_H

#include <Arduino.h>
#include <math.h>

// Model configuration
#define SENSOR_COUNT 16
#define WINDOW_SIZE 60
#define FEATURE_COUNT 16

// Stores one complete 60-timestep temperature window
struct TemperatureWindow {
    float readings[WINDOW_SIZE][SENSOR_COUNT];
};

// Stores all 16 extracted features
struct ThermalFeatures {
    float values[FEATURE_COUNT];
};

// Feature order must exactly match Python training
extern const char* const FEATURE_NAMES[FEATURE_COUNT];

// Calculate all 16 thermal features
bool extractFeatures(
    const TemperatureWindow& window,
    ThermalFeatures& features
);

#endif
