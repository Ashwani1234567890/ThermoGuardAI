#include "temperature_buffer.h"

TemperatureBuffer::TemperatureBuffer() {
    writeIndex = 0;
    totalSamples = 0;

    // Initialize the temperature window
    for (int t = 0; t < WINDOW_SIZE; t++) {
        for (int s = 0; s < SENSOR_COUNT; s++) {
            window.readings[t][s] = 0.0f;
        }
    }
}

void TemperatureBuffer::addReading(
    const float readings[SENSOR_COUNT]
) {
    if (totalSamples < WINDOW_SIZE) {

        // Fill the buffer initially
        for (int s = 0; s < SENSOR_COUNT; s++) {
            window.readings[writeIndex][s] = readings[s];
        }

        writeIndex++;
        totalSamples++;

    } else {

        // Remove the oldest reading
        for (int t = 0; t < WINDOW_SIZE - 1; t++) {
            for (int s = 0; s < SENSOR_COUNT; s++) {
                window.readings[t][s] =
                    window.readings[t + 1][s];
            }
        }

        // Insert the newest reading
        for (int s = 0; s < SENSOR_COUNT; s++) {
            window.readings[WINDOW_SIZE - 1][s] = readings[s];
        }
    }
}

bool TemperatureBuffer::isReady() const {
    return totalSamples >= WINDOW_SIZE;
}

const TemperatureWindow& TemperatureBuffer::getWindow() const {
    return window;
}

int TemperatureBuffer::getSampleCount() const {
    return totalSamples;
}