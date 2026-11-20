#ifndef THERMAL_CONTROLLER_H
#define THERMAL_CONTROLLER_H

#include "temperature_buffer.h"
#include "thermal_inference.h"

class ThermalController {
private:
    TemperatureBuffer temperatureBuffer;

public:
    ThermalController();

    // Add one set of 16 calibrated temperatures.
    // Returns true when a new prediction is available.
    bool processTemperatureReading(
        const float temperatures[SENSOR_COUNT],
        ThermalPrediction& prediction
    );

    // Check whether the 60-reading window is full.
    bool isReady() const;

    // Get the number of readings collected.
    int getSampleCount() const;
};

#endif