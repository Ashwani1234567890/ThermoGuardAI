#ifndef SENSOR_READER_H
#define SENSOR_READER_H

#include <Arduino.h>

#define SENSOR_COUNT 16

// ESP32 pin connected to the multiplexer common output
#define MUX_SIG_PIN 34

// CD74HC4067 channel selection pins
#define MUX_S0_PIN 16
#define MUX_S1_PIN 17
#define MUX_S2_PIN 18
#define MUX_S3_PIN 19

// Initialize multiplexer and ADC
void initializeSensorReader();

// Read one selected multiplexer channel
int readSensorRaw(uint8_t channel);

// Read all 16 sensor channels
void readAllSensorsRaw(int readings[SENSOR_COUNT]);

#endif