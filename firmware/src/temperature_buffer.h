#ifndef TEMPERATURE_BUFFER_H
#define TEMPERATURE_BUFFER_H

#include "feature_extractor.h"

class TemperatureBuffer {
private:
    TemperatureWindow window;
    int writeIndex;
    int totalSamples;

public:
    TemperatureBuffer();

    void addReading(const float readings[SENSOR_COUNT]);

    bool isReady() const;

    const TemperatureWindow& getWindow() const;

    int getSampleCount() const;
};

#endif