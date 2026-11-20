
#include "sensor_reader.h"

void initializeSensorReader() {

    // Configure multiplexer selection pins
    pinMode(MUX_S0_PIN, OUTPUT);
    pinMode(MUX_S1_PIN, OUTPUT);
    pinMode(MUX_S2_PIN, OUTPUT);
    pinMode(MUX_S3_PIN, OUTPUT);

    // Configure multiplexer output pin
    pinMode(MUX_SIG_PIN, INPUT);

    // Configure ESP32 ADC
    analogReadResolution(12);
    analogSetPinAttenuation(MUX_SIG_PIN, ADC_11db);

    Serial.println("Sensor reader initialized.");
    Serial.println("CD74HC4067: 16 channels ready.");
}

int readSensorRaw(uint8_t channel) {

    // Reject invalid channel numbers
    if (channel >= SENSOR_COUNT) {
        return -1;
    }

    // Select multiplexer channel using binary addressing
    digitalWrite(MUX_S0_PIN, (channel & 0x01) ? HIGH : LOW);
    digitalWrite(MUX_S1_PIN, (channel & 0x02) ? HIGH : LOW);
    digitalWrite(MUX_S2_PIN, (channel & 0x04) ? HIGH : LOW);
    digitalWrite(MUX_S3_PIN, (channel & 0x08) ? HIGH : LOW);

    // Allow signal to settle
    delayMicroseconds(50);

    // Discard first reading after channel switching
    analogRead(MUX_SIG_PIN);

    // Average five ADC readings
    long total = 0;

    for (int i = 0; i < 5; i++) {

        int adcValue = analogRead(MUX_SIG_PIN);

        // Reject values outside the 12-bit ADC range
        if (adcValue < 0 || adcValue > 4095) {
            return -1;
        }

        total += adcValue;
    }

    return static_cast<int>(total / 5);
}

void readAllSensorsRaw(int readings[SENSOR_COUNT]) {

    for (int channel = 0; channel < SENSOR_COUNT; channel++) {

        readings[channel] = readSensorRaw(channel);
    }
}
