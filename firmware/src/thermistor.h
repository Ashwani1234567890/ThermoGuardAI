#ifndef THERMISTOR_H
#define THERMISTOR_H

#include <Arduino.h>

#define NTC_NOMINAL_RESISTANCE 10000.0f
#define NTC_REFERENCE_TEMPERATURE 25.0f

// Beta value will be configured after obtaining the datasheet.
#define NTC_BETA 0.0f

// Convert raw ADC reading into temperature in Celsius.
bool convertAdcToTemperatureC(
    int adcRaw,
    float& temperatureC
);

#endif