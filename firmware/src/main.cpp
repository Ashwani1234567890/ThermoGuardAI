
#include <Arduino.h>
#include "sensor_reader.h"

int sensorReadings[SENSOR_COUNT];

void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println();
    Serial.println("================================");
    Serial.println("THERMAL THREAT DETECTION SYSTEM");
    Serial.println("ESP32 INITIALIZATION");
    Serial.println("================================");

    initializeSensorReader();

    Serial.println("Sensor acquisition started.");
}

void loop() {

    // Read all 16 multiplexer channels
    readAllSensorsRaw(sensorReadings);

    bool scanValid = true;

    Serial.println("\n16-CHANNEL SENSOR READINGS");

    for (int i = 0; i < SENSOR_COUNT; i++) {

        Serial.print("NTC ");
        Serial.print(i + 1);
        Serial.print(": ");

        if (sensorReadings[i] < 0 || sensorReadings[i] > 4095) {
            Serial.println("INVALID ADC READING");
            scanValid = false;
        } else {
            Serial.println(sensorReadings[i]);
        }
    }

    if (scanValid) {
        Serial.println("SCAN STATUS: VALID");
    } else {
        Serial.println("SCAN STATUS: SENSOR READING ERROR");
    }

    delay(1000);
}
