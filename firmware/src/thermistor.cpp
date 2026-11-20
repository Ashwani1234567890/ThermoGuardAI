#include "thermistor.h"

bool convertAdcToTemperatureC(
    int adcRaw,
    float& temperatureC
) {
    // Reject invalid ADC readings.
    if (adcRaw <= 0 || adcRaw >= 4095) {
        return false;
    }

    // Beta value and voltage-divider configuration
    // must be confirmed before conversion.
    if (NTC_BETA <= 0.0f) {
        return false;
    }

    // Temperature conversion will be implemented
    // after the thermistor specifications are verified.
    return false;
}