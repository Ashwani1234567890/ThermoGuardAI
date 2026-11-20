#pragma once

#include <Arduino.h>

// Validated breadboard pin-map; relay contacts are demonstration-only.
// Leave COM/NO/NC disconnected: this firmware is not a load safety controller.
#define LED_GREEN_PIN  27
#define LED_YELLOW_PIN 26
#define LED_RED_PIN    25
#define RELAY_PIN      33
#define BUZZER_PIN     32
#define MUX_SELECT_A_PIN 18
#define MUX_SELECT_B_PIN 19
#define MUX_SELECT_C_PIN 21
#define LOWER_BANK_ADC_PIN 34
#define UPPER_BANK_ADC_PIN 35

constexpr uint8_t SENSOR_COUNT = 16;
constexpr uint8_t GRID_WIDTH = 4;
constexpr uint32_t SCAN_INTERVAL_MS = 200;
constexpr uint32_t MUX_SETTLE_US = 50;
constexpr uint32_t SCAN_DEADLINE_MS = 120;
constexpr uint32_t FRAME_STALE_MS = 750;
constexpr uint16_t ALARM_FREQUENCY_HZ = 2300;

constexpr float DIVIDER_RESISTANCE_OHMS = 10000.0f;
constexpr float THERMISTOR_REFERENCE_OHMS = 10000.0f;
constexpr float THERMISTOR_REFERENCE_K = 298.15f;
constexpr float THERMISTOR_BETA_K = 3950.0f;
constexpr float ADC_FULL_SCALE = 4095.0f;
constexpr float WARNING_TEMPERATURE_C = 45.0f;
constexpr float CRITICAL_TEMPERATURE_C = 60.0f;
constexpr float CRITICAL_RISE_C_PER_SECOND = 2.5f;
constexpr float TEMPERATURE_HYSTERESIS_C = 2.0f;
constexpr float RISE_HYSTERESIS_C_PER_SECOND = 0.5f;
constexpr float TEMP_FILTER_ALPHA = 0.35f;

// Offsets apply to live NTC measurements, before filtering and raw override.
// Calibrate each contact sensor against an independent reference.
constexpr float PIXEL_OFFSET_C[SENSOR_COUNT] = {
    0, 0, 0, 0,
    0, 0, 0, 0,
    0, 0, 0, 0,
    0, 0, 0, 0
};

constexpr int SENSOR_LOW_RAIL_LIMIT = 8;
constexpr int SENSOR_HIGH_RAIL_LIMIT = 4087;

constexpr uint8_t STATE_NORMAL = 0;
constexpr uint8_t STATE_WARNING = 1;
constexpr uint8_t STATE_CRITICAL = 2;
constexpr uint8_t STATE_SENSOR_FAULT = 3;

constexpr char WIFI_SSID[] = "YOUR_WIFI_SSID";
constexpr char WIFI_PASSWORD[] = "YOUR_WIFI_PASSWORD";
constexpr char UDP_DESTINATION[] = "192.168.1.222";
constexpr uint16_t UDP_DESTINATION_PORT = 5005;
constexpr uint16_t TELEMETRY_NODE_ID = 101;
constexpr uint32_t UDP_REPEAT_MS = 2000;
constexpr uint32_t UDP_MIN_INTERVAL_MS = 200;
constexpr bool TRANSMIT_SYNTHETIC_UDP = false;
constexpr uint32_t WIFI_RETRY_MS = 15000;

// HTTP is deliberately small: no general-purpose form/JSON request parser.
constexpr size_t HTTP_REQUEST_LIMIT = 768;
constexpr size_t HTTP_BODY_LIMIT = 16;
constexpr uint32_t HTTP_SOCKET_DEADLINE_MS = 250;
constexpr size_t STATUS_JSON_CAPACITY = 6144;
constexpr uint8_t RECENT_EVENT_COUNT = 12;
