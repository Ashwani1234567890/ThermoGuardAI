#include "config.h"
#include <WiFi.h>
#include <WiFiUdp.h>
#include <WebServer.h>
#include <lwip/sockets.h>
#include <math.h>
#include <limits.h>
#include <stdarg.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

WiFiUDP udp;

#pragma pack(push, 1)
struct ThermalAlertPacket {
    uint16_t node_id;
    uint32_t sequence_num;
    uint32_t timestamp_ms;
    uint8_t status_code;
    uint8_t threat_score;
    int16_t max_temp_c100;
    int16_t dT_dt_c100;
    uint8_t hotspot_x;
    uint8_t hotspot_y;
    uint16_t ambient_c100;
    uint32_t crc32;
};
#pragma pack(pop)
static_assert(sizeof(ThermalAlertPacket) == 24, "Telemetry layout changed");
// The struct documents compatibility only. Its memory is never sent directly.

enum Source : uint8_t { LIVE, DEMO_NORMAL, DEMO_HOTSPOT, DEMO_RISING, DEMO_FAULT };
enum SensorFault : uint8_t { SENSOR_OK, SENSOR_OPEN, SENSOR_SHORT, SENSOR_INVALID };

struct Frame {
    float raw[SENSOR_COUNT];
    float filtered[SENSOR_COUNT];
    float rise[SENSOR_COUNT];
    uint32_t sampled[SENSOR_COUNT];
    SensorFault faults[SENSOR_COUNT];
    uint16_t sampledMask;
    uint16_t validMask;
    uint32_t started;
    uint32_t completed;
    Source source;
    bool complete;
};

struct Metrics {
    float maxTemp;
    float rawMax;
    float mean;
    float rise;
    float gradient;
    uint8_t area;
    uint8_t hotX;
    uint8_t hotY;
    uint8_t score;
};

Frame frames[2] = {};
uint8_t frontIndex = 0;
bool haveFrame = false;
bool scanning = false;
bool waitingForSettle = false;
uint8_t scanChannel = 0;
uint32_t settleStartedUs = 0;
uint32_t nextScanTime = 0;
Source source = LIVE;
uint32_t sourceStarted = 0;

float baselineTemp[SENSOR_COUNT] = {};
uint32_t baselineTime[SENSOR_COUNT] = {};
bool baselineValid[SENSOR_COUNT] = {};
bool healthyBaseline = false;
bool acquisitionFault = true;
bool criticalLatched = false;
bool warningLatched = false;
uint8_t currentState = STATE_SENSOR_FAULT;
bool buzzerRunning = false;
bool udpTransitionPending = true;

Metrics metrics = {NAN, NAN, NAN, NAN, NAN, 0, 255, 255, 100};
uint32_t frameSequence = 0;
uint32_t processingUs = 0;
uint32_t lastUdpAttempt = 0;
uint32_t udpAttempts = 0;
uint32_t udpSubmitted = 0;
uint32_t udpLocalErrors = 0;
uint32_t udpSkippedWifi = 0;
uint32_t udpSkippedSynthetic = 0;
bool udpAttempted = false;
uint32_t nextWifiRetry = 0;
uint32_t wifiReconnectAttempts = 0;
bool wifiWasConnected = false;
IPAddress udpDestination;

struct Event {
    uint32_t time;
    char text[88];
};
Event events[RECENT_EVENT_COUNT] = {};
uint8_t eventHead = 0;
uint8_t eventCount = 0;

const char* sourceName(Source s) {
    switch (s) {
        case LIVE: return "live";
        case DEMO_NORMAL: return "synthetic-normal";
        case DEMO_HOTSPOT: return "synthetic-hotspot";
        case DEMO_RISING: return "synthetic-rising";
        default: return "synthetic-fault";
    }
}

const char* stateName(uint8_t s) {
    switch (s) {
        case STATE_NORMAL: return "NORMAL";
        case STATE_WARNING: return "WARNING";
        case STATE_CRITICAL: return "CRITICAL";
        default: return "FAULT";
    }
}

void addEvent(const char* format, ...) {
    Event& e = events[eventHead];
    e.time = millis();
    va_list args;
    va_start(args, format);
    vsnprintf(e.text, sizeof(e.text), format, args);
    va_end(args);
    eventHead = (eventHead + 1) % RECENT_EVENT_COUNT;
    if (eventCount < RECENT_EVENT_COUNT) ++eventCount;

    // Never wait for a congested USB/UART console.
    char line[120];
    int n = snprintf(line, sizeof(line), "[%lu ms] %s\n",
                     (unsigned long)e.time, e.text);
    if (n > 0 && n < int(sizeof(line)) && Serial.availableForWrite() >= n) {
        Serial.write(reinterpret_cast<const uint8_t*>(line), size_t(n));
    }
}

void resetBaselines() {
    memset(baselineValid, 0, sizeof(baselineValid));
    healthyBaseline = false;
}

bool frameStale(uint32_t now) {
    return !haveFrame || !frames[frontIndex].complete ||
           now - frames[frontIndex].completed >= FRAME_STALE_MS;
}

void updateOutputs(uint32_t now) {
    const bool fault = currentState == STATE_SENSOR_FAULT;
    const bool alarm = fault || currentState == STATE_CRITICAL;
    digitalWrite(LED_GREEN_PIN, currentState == STATE_NORMAL ? HIGH : LOW);
    digitalWrite(LED_YELLOW_PIN,
                 fault || currentState == STATE_WARNING ? HIGH : LOW);
    digitalWrite(LED_RED_PIN, alarm ? HIGH : LOW);
    digitalWrite(RELAY_PIN, alarm ? HIGH : LOW);

    // Passive piezo: active-high square wave, not a silent DC HIGH.
    const bool sound = currentState == STATE_CRITICAL ||
                       (fault && now % 1000u < 250u);
    if (sound != buzzerRunning) {
        if (sound) tone(BUZZER_PIN, ALARM_FREQUENCY_HZ);
        else {
            noTone(BUZZER_PIN);
            digitalWrite(BUZZER_PIN, LOW);
        }
        buzzerRunning = sound;
    }
}

void serviceAlarms() {
    const uint32_t now = millis();
    const bool incompleteOverdue =
        scanning && now - frames[1 - frontIndex].started >= SCAN_DEADLINE_MS;
    const bool fault = acquisitionFault || frameStale(now) || incompleteOverdue;

    if (fault) {
        resetBaselines();
        metrics.score = 100; // Fault sentinel, not a thermal probability.
    }
    const uint8_t desired = fault ? STATE_SENSOR_FAULT :
        criticalLatched ? STATE_CRITICAL :
        warningLatched ? STATE_WARNING : STATE_NORMAL;
    if (desired != currentState) {
        currentState = desired;
        udpTransitionPending = true;
        addEvent("Alarm %s; source %s", stateName(desired), sourceName(source));
    }
    updateOutputs(now);
}

float readTemperature(int raw, SensorFault& fault) {
    if (raw <= SENSOR_LOW_RAIL_LIMIT) {
        fault = SENSOR_OPEN;
        return NAN; // Upper NTC open: lower divider resistor pulls down.
    }
    if (raw >= SENSOR_HIGH_RAIL_LIMIT) {
        fault = SENSOR_SHORT;
        return NAN;
    }
    const float resistance =
        DIVIDER_RESISTANCE_OHMS * (ADC_FULL_SCALE / float(raw) - 1.0f);
    const float inverseK = 1.0f / THERMISTOR_REFERENCE_K +
        logf(resistance / THERMISTOR_REFERENCE_OHMS) / THERMISTOR_BETA_K;
    const float t = 1.0f / inverseK - 273.15f;
    if (!isfinite(t) || inverseK <= 0) {
        fault = SENSOR_INVALID;
        return NAN;
    }
    fault = SENSOR_OK;
    return t;
}

// Real ESP32 ADC is not perfectly ratiometric/linear at ADC_11db, and may
// saturate below 3.3 V. These counts/B-equation are a prototype approximation.
// Characterize ADC voltage, divider tolerances, mux settling, contact coupling,
// and thermistor R/T curve on the real board. Offsets cannot repair all errors.
// Rail faults identify open/short-like voltage, not every possible wiring fault.

void setMuxChannel(uint8_t channel) {
    digitalWrite(MUX_SELECT_A_PIN, channel & 1);
    digitalWrite(MUX_SELECT_B_PIN, (channel >> 1) & 1);
    digitalWrite(MUX_SELECT_C_PIN, (channel >> 2) & 1);
    settleStartedUs = micros();
    waitingForSettle = true;
}

float syntheticTemperature(uint8_t index, uint32_t now, SensorFault& fault) {
    fault = SENSOR_OK;
    if (source == DEMO_FAULT && index == 5) {
        fault = SENSOR_OPEN;
        return NAN;
    }
    float t = 25.0f + 0.15f * float(index % GRID_WIDTH);
    if (source == DEMO_HOTSPOT) {
        if (index == 5) t = 65.0f;
        else if (index == 1 || index == 4 || index == 6 || index == 9) t = 48.0f;
    }
    if (source == DEMO_RISING && (index == 5 || index == 6)) {
        // 3 C/s: filtered rise alert in roughly one second; 60 C in 12 s.
        t += fminf(65.0f, 3.0f * float(now - sourceStarted) / 1000.0f);
    }
    return t;
}

float boundedUnit(float x) {
    return fmaxf(0.0f, fminf(1.0f, x));
}

void processFrame(Frame& f) {
    const uint32_t startedUs = micros();
    const bool healthy = f.complete && f.validMask == 0xffff;
    if (!healthy || !healthyBaseline) {
        memset(baselineValid, 0, sizeof(baselineValid));
    }

    metrics = {NAN, NAN, NAN, NAN, NAN, 0, 255, 255, 0};
    float sum = 0;
    uint8_t count = 0;
    for (uint8_t i = 0; i < SENSOR_COUNT; ++i) {
        f.filtered[i] = NAN;
        f.rise[i] = NAN;
        if (!(f.validMask & (uint16_t(1) << i))) {
            baselineValid[i] = false;
            continue;
        }
        const uint32_t dt = f.sampled[i] - baselineTime[i];
        const bool usableBaseline = healthy && baselineValid[i] &&
                                    dt > 0 && dt < FRAME_STALE_MS;
        f.filtered[i] = usableBaseline ?
            baselineTemp[i] + TEMP_FILTER_ALPHA * (f.raw[i] - baselineTemp[i]) :
            f.raw[i];
        if (usableBaseline) {
            f.rise[i] = (f.filtered[i] - baselineTemp[i]) * 1000.0f / float(dt);
            if (!isfinite(metrics.rise) || f.rise[i] > metrics.rise)
                metrics.rise = f.rise[i];
        }
        baselineTemp[i] = f.filtered[i];
        baselineTime[i] = f.sampled[i];
        baselineValid[i] = healthy;

        sum += f.filtered[i];
        ++count;
        if (!isfinite(metrics.maxTemp) || f.filtered[i] > metrics.maxTemp) {
            metrics.maxTemp = f.filtered[i];
            metrics.hotX = i % GRID_WIDTH;
            metrics.hotY = i / GRID_WIDTH;
        }
        if (!isfinite(metrics.rawMax) || f.raw[i] > metrics.rawMax)
            metrics.rawMax = f.raw[i];
        if (f.filtered[i] >= WARNING_TEMPERATURE_C) ++metrics.area;
    }
    if (count) metrics.mean = sum / count;

    // Four-connected neighbors, once per edge. No interpolation of invalid cells.
    for (uint8_t i = 0; i < SENSOR_COUNT; ++i) {
        if (!isfinite(f.filtered[i])) continue;
        const uint8_t neighbors[2] = {
            uint8_t(i % GRID_WIDTH < GRID_WIDTH - 1 ? i + 1 : 255),
            uint8_t(i + GRID_WIDTH < SENSOR_COUNT ? i + GRID_WIDTH : 255)
        };
        for (uint8_t j : neighbors) {
            if (j == 255 || !isfinite(f.filtered[j])) continue;
            const float delta = fabsf(f.filtered[i] - f.filtered[j]);
            if (!isfinite(metrics.gradient) || delta > metrics.gradient)
                metrics.gradient = delta;
        }
    }

    // Deterministic demonstration feature score, NOT trained ML, likelihood,
    // or a validated thermal-runaway predictor. Area is a count, not cm².
    const float tempFeature = isfinite(metrics.maxTemp) ?
        boundedUnit((metrics.maxTemp - 30.0f) / 30.0f) : 0;
    const float riseFeature = isfinite(metrics.rise) ?
        boundedUnit(metrics.rise / CRITICAL_RISE_C_PER_SECOND) : 0;
    const float gradientFeature = isfinite(metrics.gradient) ?
        boundedUnit(metrics.gradient / 20.0f) : 0;
    metrics.score = healthy ? uint8_t(lroundf(
        45 * tempFeature + 30 * riseFeature + 15 * gradientFeature +
        10 * boundedUnit(float(metrics.area) / 4.0f))) : 100;

    if (healthy) {
        const bool triggerCritical =
            metrics.rawMax >= CRITICAL_TEMPERATURE_C ||
            (isfinite(metrics.rise) &&
             metrics.rise >= CRITICAL_RISE_C_PER_SECOND);
        const bool holdCritical =
            metrics.rawMax >= CRITICAL_TEMPERATURE_C - TEMPERATURE_HYSTERESIS_C ||
            metrics.maxTemp >= CRITICAL_TEMPERATURE_C - TEMPERATURE_HYSTERESIS_C ||
            (isfinite(metrics.rise) && metrics.rise >=
             CRITICAL_RISE_C_PER_SECOND - RISE_HYSTERESIS_C_PER_SECOND);
        criticalLatched = triggerCritical || (criticalLatched && holdCritical);
        warningLatched = metrics.maxTemp >= WARNING_TEMPERATURE_C ||
            (warningLatched && metrics.maxTemp >=
             WARNING_TEMPERATURE_C - TEMPERATURE_HYSTERESIS_C);
    }
    healthyBaseline = healthy;
    acquisitionFault = !healthy;
    processingUs = micros() - startedUs;
}

void beginScan(uint32_t now) {
    Frame& f = frames[1 - frontIndex];
    f = {};
    f.started = now;
    f.source = source;
    scanning = true;
    scanChannel = 0;
    setMuxChannel(0);
}

void serviceScan() {
    const uint32_t now = millis();
    if (!scanning) {
        if (int32_t(now - nextScanTime) >= 0) beginScan(now);
        return;
    }
    Frame& f = frames[1 - frontIndex];
    if (now - f.started >= SCAN_DEADLINE_MS) {
        scanning = false;
        acquisitionFault = true;
        resetBaselines();
        nextScanTime = now;
        addEvent("Incomplete scan discarded; local fault");
        return;
    }
    if (waitingForSettle && uint32_t(micros() - settleStartedUs) < MUX_SETTLE_US)
        return;
    waitingForSettle = false;

    // At most one shared channel / two pixels per call; no delay/catch-up loop.
    for (uint8_t bank = 0; bank < 2; ++bank) {
        const uint8_t i = scanChannel + 8 * bank;
        SensorFault fault = SENSOR_OK;
        float t;
        if (source == LIVE) {
            const int pin = bank == 0 ? LOWER_BANK_ADC_PIN : UPPER_BANK_ADC_PIN;
            analogRead(pin); // Discard first sample after switching.
            t = readTemperature(analogRead(pin), fault);
            if (fault == SENSOR_OK) t += PIXEL_OFFSET_C[i];
        } else {
            t = syntheticTemperature(i, millis(), fault);
        }
        if (fault == SENSOR_OK && !isfinite(t)) fault = SENSOR_INVALID;
        f.raw[i] = fault == SENSOR_OK ? t : NAN;
        f.faults[i] = fault;
        f.sampled[i] = millis();
        f.sampledMask |= uint16_t(1) << i;
        if (fault == SENSOR_OK) {
            f.validMask |= uint16_t(1) << i;
            // Unfiltered override takes effect before finishing the frame.
            if (t >= CRITICAL_TEMPERATURE_C) criticalLatched = true;
        } else {
            acquisitionFault = true;
            resetBaselines();
        }
        serviceAlarms();
    }

    if (++scanChannel < 8) {
        setMuxChannel(scanChannel);
        return;
    }
    f.completed = millis();
    f.complete = f.sampledMask == 0xffff;
    processFrame(f);
    frontIndex = 1 - frontIndex; // Publish only a complete, single-source frame.
    haveFrame = true;
    scanning = false;
    ++frameSequence;
    nextScanTime = f.started + SCAN_INTERVAL_MS;
    if (int32_t(millis() - nextScanTime) >= 0)
        nextScanTime = millis() + SCAN_INTERVAL_MS;
    serviceAlarms();
}

bool selectScenario(const char* name) {
    Source selected;
    if (!strcmp(name, "live")) selected = LIVE;
    else if (!strcmp(name, "normal")) selected = DEMO_NORMAL;
    else if (!strcmp(name, "hotspot")) selected = DEMO_HOTSPOT;
    else if (!strcmp(name, "rising")) selected = DEMO_RISING;
    else if (!strcmp(name, "fault")) selected = DEMO_FAULT;
    else return false;

    // Even selecting the same scenario restarts its baseline/time.
    source = selected;
    sourceStarted = millis();
    scanning = false;
    waitingForSettle = false;
    haveFrame = false;
    acquisitionFault = true;
    criticalLatched = false;
    warningLatched = false;
    resetBaselines();
    metrics = {NAN, NAN, NAN, NAN, NAN, 0, 255, 255, 100};
    nextScanTime = sourceStarted;
    udpTransitionPending = true;
    addEvent("Source %s; baseline reset", sourceName(source));
    serviceAlarms();
    return true;
}

void serviceSerial() {
    static char command[32];
    static uint8_t length = 0;
    static bool overflow = false;
    // Fixed byte budget; overflowing lines are discarded, never truncated commands.
    for (uint8_t budget = 0; budget < 32 && Serial.available(); ++budget) {
        const char c = char(Serial.read());
        if (c == '\r') continue;
        if (c == '\n') {
            command[length] = 0;
            if (overflow) addEvent("Serial command too long");
            else if (length && !selectScenario(command))
                addEvent("Commands: live normal hotspot rising fault");
            length = 0;
            overflow = false;
        } else if (length < sizeof(command) - 1 && !overflow) {
            command[length++] = c;
        } else overflow = true;
    }
}

int16_t encodeHundredths(float value) {
    if (!isfinite(value)) return INT16_MIN;
    float v = roundf(value * 100.0f);
    v = fmaxf(float(INT16_MIN + 1), fminf(float(INT16_MAX), v));
    return int16_t(v);
}

void put16(uint8_t* p, uint16_t value) {
    p[0] = uint8_t(value);
    p[1] = uint8_t(value >> 8);
}

void put32(uint8_t* p, uint32_t value) {
    for (uint8_t i = 0; i < 4; ++i) p[i] = uint8_t(value >> (8 * i));
}

uint32_t packetCrc(const uint8_t* p, size_t length) {
    // CRC-32 IEEE: reflected 0xEDB88320, init/final XOR 0xFFFFFFFF.
    uint32_t crc = 0xffffffffu;
    for (size_t i = 0; i < length; ++i) {
        crc ^= p[i];
        for (uint8_t bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ ((crc & 1) ? 0xedb88320u : 0u);
    }
    return crc ^ 0xffffffffu;
}

void serviceUdp() {
    const uint32_t now = millis();
    if (udpAttempted && now - lastUdpAttempt < UDP_MIN_INTERVAL_MS) return;
    if (!udpTransitionPending && udpAttempted &&
        now - lastUdpAttempt < UDP_REPEAT_MS) return;

    udpAttempted = true;
    lastUdpAttempt = now;
    udpTransitionPending = false;
    if (source != LIVE && !TRANSMIT_SYNTHETIC_UDP) {
        ++udpSkippedSynthetic;
        return;
    }
    if (WiFi.status() != WL_CONNECTED) {
        ++udpSkippedWifi;
        return;
    }

    uint8_t packet[24] = {};
    const bool usable = !frameStale(now) && haveFrame &&
                        frames[frontIndex].source == source;
    put16(packet + 0, TELEMETRY_NODE_ID);
    put32(packet + 2, frameSequence);
    put32(packet + 6, now);
    packet[10] = currentState;
    packet[11] = currentState == STATE_SENSOR_FAULT ? 100 : metrics.score;
    put16(packet + 12, uint16_t(encodeHundredths(usable ? metrics.maxTemp : NAN)));
    put16(packet + 14, uint16_t(encodeHundredths(usable ? metrics.rise : NAN)));
    packet[16] = usable ? metrics.hotX : 255;
    packet[17] = usable ? metrics.hotY : 255;
    put16(packet + 18, 0); // Reserved ambient, no ambient sensor wired.
    put32(packet + 20, packetCrc(packet, 20));

    ++udpAttempts;
    bool submitted = false;
    if (udp.beginPacket(udpDestination, UDP_DESTINATION_PORT)) {
        const size_t n = udp.write(packet, sizeof(packet));
        const int result = udp.endPacket();
        submitted = n == sizeof(packet) && result == 1;
    }
    if (submitted) ++udpSubmitted;
    else ++udpLocalErrors;
    // endPacket() means local submission only; no delivery/acknowledgment claim.
}

void serviceWifi() {
    const uint32_t now = millis();
    const bool connected = WiFi.status() == WL_CONNECTED;
    if (connected != wifiWasConnected) {
        wifiWasConnected = connected;
        if (connected) {
            addEvent("Dashboard http://%s/; UDP unacknowledged",
                     WiFi.localIP().toString().c_str());
            udpTransitionPending = true;
        } else addEvent("WiFi disconnected; local alarms remain active");
    }
    if (!connected && int32_t(now - nextWifiRetry) >= 0) {
        nextWifiRetry = now + WIFI_RETRY_MS;
        ++wifiReconnectAttempts;
        WiFi.reconnect(); // Scheduled attempt, no connection wait.
    }
}

const char PAGE[] PROGMEM = R"rawliteral(
<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Contact Thermal Monitor</title><style>
:root{--bg:#F7F7F5;--card:#fff;--border:#E5E5E0;--text:#1C1C1C;--muted:#6B6B66}
@media(prefers-color-scheme:dark){:root{--bg:#141413;--card:#1D1D1B;--border:#2E2E2B;--text:#F0EFEA;--muted:#9A9A93}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:720px;margin:auto;padding:20px 16px}h1{font-size:23px;margin-bottom:6px}h2{font-size:17px}
p,small{color:var(--muted);line-height:1.5}.dot{display:inline-block;width:9px;height:9px;border-radius:50%;background:#777;margin-right:7px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.card,section{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:15px}
.card{height:112px}.label{font-size:13px;color:var(--muted)}.value{font-size:32px;font-weight:600;font-variant-numeric:tabular-nums;margin-top:8px}
section{margin-top:14px}button{min-height:44px;padding:8px 13px;margin:4px;border:1px solid var(--border);border-radius:8px;background:#E28C65;color:#1C1C1C;font:inherit;cursor:pointer}
button:focus-visible{outline:3px solid #2E7D32}.heat{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}
.pixel{height:65px;border:1px solid var(--border);border-radius:8px;text-align:center;padding:10px 2px;font-variant-numeric:tabular-nums}
.pixel small{display:block;font-size:11px;color:inherit}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;line-height:1.6}
#alarm{font-weight:600}footer{font-size:12px;color:var(--muted);margin-top:18px}
</style></head><body><main>
<h1>Contact Thermal Monitor</h1><p><span class="dot" id="dot"></span><span id="connection">Connecting…</span></p>
<p id="alarm">Local alarms: --</p>
<div class="cards">
<div class="card"><div class="label">Feature score / 100</div><div class="value" id="score">--</div></div>
<div class="card"><div class="label">Maximum · °C</div><div class="value" id="max">--</div></div>
<div class="card"><div class="label">Mean · °C</div><div class="value" id="mean">--</div></div>
<div class="card"><div class="label">Fastest rise · °C/s</div><div class="value" id="rise">--</div></div>
<div class="card"><div class="label">Neighbor gradient · °C</div><div class="value" id="gradient">--</div></div>
<div class="card"><div class="label">Hot area · pixels ≥45°C</div><div class="value" id="area">--</div></div>
</div>
<section><h2>4 × 4 contact heatmap</h2><p id="source">Source: --</p><div class="heat" id="heat"></div>
<p id="coordinates">Hotspot: --</p><small>Row-major, zero-based coordinates. Invalid cells are never replaced with normal temperatures.</small></section>
<section><h2>Acquisition and labeled demos</h2>
<div id="controls"><button data-mode="live">Live NTC</button><button data-mode="normal">Synthetic normal</button>
<button data-mode="hotspot">Synthetic hotspot</button><button data-mode="rising">Synthetic rising</button>
<button data-mode="fault">Synthetic fault</button></div><p id="controlStatus">Live acquisition is the startup default. Rising alerts in under 30 seconds.</p></section>
<section><h2>System and telemetry</h2><pre id="system">--</pre></section>
<section><h2>Recent events</h2><pre id="events">--</pre></section>
<p>Demonstration thresholds: warning 45°C, critical 60°C or rise 2.5°C/s, with hysteresis.
The feature score is deterministic, not trained ML or validated thermal-runaway prediction.
Fault score 100 indicates acquisition failure, not thermal probability.</p>
<p>Relay contacts: demonstration-only, no load connected. Contact sensors are not a thermal camera.
Real-board ADC, thermistor and contact calibration is required. Cooperative scheduling is not hard real-time.</p>
<footer id="footer">ESP32 DevKit V1 · uptime --</footer>
</main><script>
const $=id=>document.getElementById(id);
const fmt=v=>v===null||v===undefined?'--':Number(v).toFixed(1);
const faults=['OK','Open / low rail','Short / high rail','Invalid'];
let last=0,data=null,failed=false;
for(let i=0;i<16;i++){let e=document.createElement('div');e.className='pixel';e.textContent='--';$('heat').appendChild(e)}
function connection(){
let age=last?(Date.now()-last)/1000:Infinity;
let bad=failed||age>6, stale=data&&data.stale;
$('dot').style.background=bad||stale?'#777':'#2E7D32';
$('connection').textContent=bad?'Disconnected, retrying':stale?'Acquisition stale / unavailable':`Connected, updated ${Math.floor(age)} s ago`;
}
async function request(url,opts={}){
let controller=new AbortController(),timer=setTimeout(()=>controller.abort(),1800);
try{let r=await fetch(url,{...opts,signal:controller.signal,cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);return await r.json()}
finally{clearTimeout(timer)}
}
async function poll(){
try{
data=await request('/api/status');last=Date.now();failed=false;
let d=data;
for(let k of ['score','max','mean','rise','gradient'])$(k).textContent=d.stale?'--':fmt(d[k]);
$('area').textContent=d.stale?'--':d.area;
$('alarm').textContent=`Local alarms: ${d.state} · relay ${d.relay?'ON':'OFF'} · buzzer ${d.buzzer?'sounding':'off'}`;
$('source').textContent=`Source: ${d.source}${d.synthetic?' — SYNTHETIC DEMO, not live sensor data':''}`;
$('coordinates').textContent=`Hotspot: ${d.hot_x===255?'--':`(${d.hot_x}, ${d.hot_y})`} · valid mask 0x${d.valid_mask.toString(16).padStart(4,'0')} · raw max ${fmt(d.raw_max)}°C`;
[...$('heat').children].forEach((e,i)=>{
let t=d.heatmap[i];e.textContent=d.stale||t===null?'--':fmt(t)+'°';
let s=document.createElement('small');s.textContent=`${i%4},${Math.floor(i/4)} · ${faults[d.faults[i]]||'Invalid'}`;e.appendChild(s);
e.style.background=d.stale||t===null?'var(--card)':`hsl(${Math.max(0,Math.min(120,120-(t-25)*3.4))} 65% 84%)`;
e.style.color=d.stale||t===null?'var(--text)':'#1C1C1C';
});
$('system').textContent=`Frame ${d.frame_sequence} · age ${d.frame_age_ms===null?'--':d.frame_age_ms+' ms'} · scan active ${d.scan_active}
Processing ${d.processing_us} µs · free heap ${d.free_heap} bytes
WiFi ${d.wifi?'connected':'disconnected'} · ${d.ip} · RSSI ${d.rssi===null?'--':d.rssi+' dBm'}
Reconnect attempts ${d.wifi_reconnect_attempts}
UDP ${d.udp_destination} · local attempts ${d.udp_attempts}
Submitted ${d.udp_submitted} (UNACKNOWLEDGED, not delivered) · local errors ${d.udp_errors}
Skipped: WiFi ${d.udp_skipped_wifi}, synthetic ${d.udp_skipped_synthetic}
Synthetic UDP ${d.synthetic_udp_enabled?'enabled: wire has no source field':'disabled by default'}`;
$('events').textContent=d.events.map(e=>`${(e.ms/1000).toFixed(1)}s  ${e.text}`).join('\n')||'No recent events';
$('footer').textContent=`ESP32 DevKit V1 · uptime ${Math.floor(d.uptime_ms/1000)} s`;
}catch(e){failed=true}connection();setTimeout(poll,2000);
}
$('controls').onclick=async e=>{
let mode=e.target.dataset.mode;if(!mode)return;
try{await request('/api/scenario',{method:'POST',headers:{'Content-Type':'text/plain'},body:mode});$('controlStatus').textContent='Selected '+mode+'; a fresh frame is required.'}
catch(err){$('controlStatus').textContent='Control failed: '+err.message}
};
setInterval(connection,1000);poll();
</script></body></html>
)rawliteral";

char statusJson[STATUS_JSON_CAPACITY];

class JsonWriter {
public:
    size_t length = 0;
    bool ok = true;
    void append(const char* format, ...) {
        if (!ok) return;
        va_list args;
        va_start(args, format);
        const int n = vsnprintf(statusJson + length,
                                sizeof(statusJson) - length, format, args);
        va_end(args);
        if (n < 0 || size_t(n) >= sizeof(statusJson) - length) ok = false;
        else length += size_t(n);
    }
    void number(float value) {
        if (isfinite(value)) append("%.3f", double(value));
        else append("null");
    }
    void quoted(const char* text) {
        append("\"");
        // Event strings are fixed 88-byte records, not user-provided log data.
        for (size_t i = 0; i < 88 && text[i]; ++i) {
            const unsigned char c = text[i];
            if (c == '"' || c == '\\') append("\\%c", c);
            else if (c >= 32) append("%c", c);
            else append(" ");
        }
        append("\"");
    }
};

size_t buildStatus() {
    JsonWriter j;
    const uint32_t now = millis();
    const bool stale = frameStale(now);
    const Frame& f = frames[frontIndex];
    j.append("{\"source\":\"%s\",\"synthetic\":%s,\"stale\":%s,"
             "\"state\":\"%s\",\"score\":%u,\"max\":",
             sourceName(source), source == LIVE ? "false" : "true",
             stale ? "true" : "false", stateName(currentState),
             currentState == STATE_SENSOR_FAULT ? 100 : metrics.score);
    j.number(stale ? NAN : metrics.maxTemp);
    j.append(",\"raw_max\":"); j.number(stale ? NAN : metrics.rawMax);
    j.append(",\"mean\":"); j.number(stale ? NAN : metrics.mean);
    j.append(",\"rise\":"); j.number(stale ? NAN : metrics.rise);
    j.append(",\"gradient\":"); j.number(stale ? NAN : metrics.gradient);
    j.append(",\"area\":%u,\"hot_x\":%u,\"hot_y\":%u,\"valid_mask\":%u,"
             "\"heatmap\":[", stale ? 0 : metrics.area,
             stale ? 255 : metrics.hotX, stale ? 255 : metrics.hotY,
             haveFrame ? f.validMask : 0);
    for (uint8_t i = 0; i < SENSOR_COUNT; ++i) {
        if (i) j.append(",");
        j.number(!haveFrame ? NAN : f.filtered[i]);
    }
    j.append("],\"faults\":[");
    for (uint8_t i = 0; i < SENSOR_COUNT; ++i)
        j.append("%s%u", i ? "," : "", haveFrame ? f.faults[i] : SENSOR_INVALID);
    j.append("],\"pixel_rise\":[");
    for (uint8_t i = 0; i < SENSOR_COUNT; ++i) {
        if (i) j.append(",");
        j.number(haveFrame && !stale ? f.rise[i] : NAN);
    }
    j.append("],\"frame_age_ms\":");
    if (haveFrame) j.append("%lu", (unsigned long)(now - f.completed));
    else j.append("null");
    j.append(",\"frame_started_ms\":%lu,\"frame_completed_ms\":%lu,"
             "\"frame_sequence\":%lu,\"scan_active\":%s,\"uptime_ms\":%lu,"
             "\"free_heap\":%lu,\"processing_us\":%lu,"
             "\"relay\":%s,\"buzzer\":%s,\"led_green\":%s,"
             "\"led_yellow\":%s,\"led_red\":%s,\"wifi\":%s,\"ip\":\"%s\",\"rssi\":",
             (unsigned long)(haveFrame ? f.started : 0),
             (unsigned long)(haveFrame ? f.completed : 0),
             (unsigned long)frameSequence, scanning ? "true" : "false",
             (unsigned long)now, (unsigned long)ESP.getFreeHeap(),
             (unsigned long)processingUs,
             currentState >= STATE_CRITICAL ? "true" : "false",
             buzzerRunning ? "true" : "false",
             currentState == STATE_NORMAL ? "true" : "false",
             currentState == STATE_WARNING || currentState == STATE_SENSOR_FAULT ?
                 "true" : "false",
             currentState >= STATE_CRITICAL ? "true" : "false",
             WiFi.status() == WL_CONNECTED ? "true" : "false",
             WiFi.localIP().toString().c_str());
    if (WiFi.status() == WL_CONNECTED) j.append("%d", WiFi.RSSI());
    else j.append("null");
    j.append(",\"wifi_reconnect_attempts\":%lu,\"udp_destination\":\"%s:%u\","
             "\"udp_attempts\":%lu,\"udp_submitted\":%lu,\"udp_errors\":%lu,"
             "\"udp_skipped_wifi\":%lu,\"udp_skipped_synthetic\":%lu,"
             "\"synthetic_udp_enabled\":%s,\"udp_acknowledged\":false,\"events\":[",
             (unsigned long)wifiReconnectAttempts, UDP_DESTINATION,
             UDP_DESTINATION_PORT, (unsigned long)udpAttempts,
             (unsigned long)udpSubmitted, (unsigned long)udpLocalErrors,
             (unsigned long)udpSkippedWifi, (unsigned long)udpSkippedSynthetic,
             TRANSMIT_SYNTHETIC_UDP ? "true" : "false");
    for (uint8_t i = 0; i < eventCount; ++i) {
        const uint8_t index =
            (eventHead + RECENT_EVENT_COUNT - eventCount + i) % RECENT_EVENT_COUNT;
        j.append("%s{\"ms\":%lu,\"text\":", i ? "," : "",
                 (unsigned long)events[index].time);
        j.quoted(events[index].text);
        j.append("}");
    }
    j.append("]}");
    if (!j.ok) {
        strcpy(statusJson, "{\"error\":\"status capacity exceeded\"}");
        return strlen(statusJson);
    }
    return j.length;
}

// WebServer's standard handleClient parser accepts dynamically sized requests.
// This subclass retains its listener/lifecycle but replaces request handling
// with a fixed-capacity, cooperative HTTP subset. Only one socket is active.
// Response writes use nonblocking send(), not WiFiClient's retrying write().
// No keep-alive, chunked requests, URL decoding, query parameters, or forms.
class BoundedDashboardServer : public WebServer {
public:
    BoundedDashboardServer() : WebServer(80) {}

    void service() {
        const uint32_t now = millis();
        if (!active) {
            _currentClient = _server.available();
            if (!_currentClient) return;
            _currentClient.setTimeout(20);
            active = true;
            writing = false;
            received = 0;
            headerEnd = 0;
            bodyLength = 0;
            deadlineStarted = now;
            return;
        }
        if (now - deadlineStarted >= HTTP_SOCKET_DEADLINE_MS ||
            !_currentClient.connected()) {
            closeSocket();
            return;
        }
        if (writing) {
            writeSlice();
            return;
        }

        for (uint8_t budget = 0; budget < 96 && _currentClient.available(); ++budget) {
            if (received >= HTTP_REQUEST_LIMIT) {
                respond(413, "text/plain", "Request too large\n");
                return;
            }
            const int v = _currentClient.read();
            if (v < 0) break;
            if (v == 0) {
                respond(400, "text/plain", "Invalid request\n");
                return;
            }
            request[received++] = char(v);
            request[received] = 0;
            if (!headerEnd && received >= 4 &&
                !memcmp(request + received - 4, "\r\n\r\n", 4)) {
                headerEnd = received;
                if (!parseHeaders()) return;
            }
            if (headerEnd && received >= headerEnd + bodyLength) {
                dispatch();
                return;
            }
        }
    }

private:
    bool active = false;
    bool writing = false;
    char request[HTTP_REQUEST_LIMIT + 1] = {};
    char method[8] = {};
    char path[40] = {};
    size_t received = 0;
    size_t headerEnd = 0;
    size_t bodyLength = 0;
    uint32_t deadlineStarted = 0;
    char responseHeader[224] = {};
    size_t responseHeaderLength = 0;
    size_t responseHeaderSent = 0;
    const char* responseBody = nullptr;
    size_t responseBodyLength = 0;
    size_t responseBodySent = 0;

    void closeSocket() {
        _currentClient.stop();
        active = false;
        writing = false;
    }

    void respond(int code, const char* type, const char* body, size_t length = 0) {
        responseBody = body;
        responseBodyLength = length ? length : strlen(body);
        responseBodySent = 0;
        responseHeaderSent = 0;
        const char* reason = code == 200 ? "OK" :
            code == 404 ? "Not Found" : code == 405 ? "Method Not Allowed" :
            code == 413 ? "Payload Too Large" : "Bad Request";
        responseHeaderLength = size_t(snprintf(responseHeader, sizeof(responseHeader),
            "HTTP/1.1 %d %s\r\nContent-Type: %s\r\nContent-Length: %u\r\n"
            "Cache-Control: no-store\r\nConnection: close\r\n\r\n",
            code, reason, type, unsigned(responseBodyLength)));
        writing = true;
        deadlineStarted = millis();
    }

    bool parseHeaders() {
        char* firstEnd = strstr(request, "\r\n");
        if (!firstEnd) {
            respond(400, "text/plain", "Invalid request\n");
            return false;
        }
        *firstEnd = 0;
        char version[12] = {};
        char extra[2] = {};
        if (sscanf(request, "%7s %39s %11s %1s",
                   method, path, version, extra) != 3 ||
            (strcmp(version, "HTTP/1.1") && strcmp(version, "HTTP/1.0"))) {
            respond(400, "text/plain", "Invalid request line\n");
            return false;
        }
        bool sawLength = false;
        char* line = firstEnd + 2;
        // Total walk is bounded by the fixed request buffer.
        for (size_t lines = 0; lines < HTTP_REQUEST_LIMIT / 2; ++lines) {
            char* end = strstr(line, "\r\n");
            if (!end) {
                respond(400, "text/plain", "Invalid headers\n");
                return false;
            }
            if (end == line) break;
            *end = 0;
            char* colon = strchr(line, ':');
            if (!colon || *line == ' ' || *line == '\t') {
                respond(400, "text/plain", "Invalid header\n");
                return false;
            }
            *colon = 0;
            char* value = colon + 1;
            while (*value == ' ' || *value == '\t') ++value;
            if (!strcasecmp(line, "Transfer-Encoding")) {
                respond(400, "text/plain", "Chunked requests unsupported\n");
                return false;
            }
            if (!strcasecmp(line, "Content-Length")) {
                if (sawLength || *value < '0' || *value > '9') {
                    respond(400, "text/plain", "Invalid content length\n");
                    return false;
                }
                char* tail = nullptr;
                errno = 0;
                const unsigned long n = strtoul(value, &tail, 10);
                while (*tail == ' ' || *tail == '\t') ++tail;
                if (errno || *tail || n > HTTP_BODY_LIMIT) {
                    respond(413, "text/plain", "Body limit is 16 bytes\n");
                    return false;
                }
                bodyLength = size_t(n);
                sawLength = true;
            }
            line = end + 2;
        }
        if (headerEnd + bodyLength > HTTP_REQUEST_LIMIT) {
            respond(413, "text/plain", "Request too large\n");
            return false;
        }
        return true;
    }

    void dispatch() {
        request[headerEnd + bodyLength] = 0;
        if (!strcmp(path, "/api/scenario")) {
            if (strcmp(method, "POST")) {
                respond(405, "text/plain", "POST only\n");
            } else if (!bodyLength || !selectScenario(request + headerEnd)) {
                respond(400, "application/json", "{\"error\":\"unknown scenario\"}");
            } else {
                respond(200, "application/json", "{\"ok\":true}");
            }
        } else if (strcmp(method, "GET")) {
            respond(405, "text/plain", "GET only\n");
        } else if (bodyLength) {
            respond(400, "text/plain", "GET body unsupported\n");
        } else if (!strcmp(path, "/")) {
            respond(200, "text/html; charset=utf-8", PAGE, sizeof(PAGE) - 1);
        } else if (!strcmp(path, "/api/status")) {
            const size_t n = buildStatus();
            respond(200, "application/json", statusJson, n);
        } else {
            respond(404, "text/plain", "Not found\n");
        }
    }

    void writeSlice() {
        const bool header = responseHeaderSent < responseHeaderLength;
        const char* p = header ? responseHeader + responseHeaderSent :
                                responseBody + responseBodySent;
        size_t remaining = header ? responseHeaderLength - responseHeaderSent :
                                   responseBodyLength - responseBodySent;
        if (!remaining) {
            closeSocket();
            return;
        }
        if (remaining > 512) remaining = 512;
        const int n = ::send(_currentClient.fd(), p, remaining, MSG_DONTWAIT);
        if (n > 0) {
            if (header) responseHeaderSent += size_t(n);
            else responseBodySent += size_t(n);
        } else if (n == 0 || (errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR)) {
            closeSocket();
        }
    }
};

BoundedDashboardServer server;

void setup() {
    const uint8_t outputs[] = {
        LED_GREEN_PIN, LED_YELLOW_PIN, LED_RED_PIN, BUZZER_PIN,
        RELAY_PIN, MUX_SELECT_A_PIN, MUX_SELECT_B_PIN, MUX_SELECT_C_PIN
    };
    for (uint8_t pin : outputs) {
        digitalWrite(pin, LOW);
        pinMode(pin, OUTPUT);
    }
    pinMode(LOWER_BANK_ADC_PIN, INPUT);
    pinMode(UPPER_BANK_ADC_PIN, INPUT);
    analogReadResolution(12);
    analogSetPinAttenuation(LOWER_BANK_ADC_PIN, ADC_11db);
    analogSetPinAttenuation(UPPER_BANK_ADC_PIN, ADC_11db);
    Serial.begin(115200);
    serviceAlarms(); // Safe fault indication before any network operation.

    Serial.println("Contact thermal demonstration; LIVE NTC acquisition.");
    Serial.println("Relay contacts demonstration-only: leave all load contacts disconnected.");
    Serial.println("Serial: live | normal | hotspot | rising | fault, followed by newline.");
    Serial.println("Dashboard: http://<ESP32 DHCP address>/ (address logged on connection).");
    Serial.println("Synthetic demos are labeled; synthetic UDP is disabled by default.");
    Serial.println("UDP 192.168.1.222:5005: local submission, unacknowledged, NOT delivered.");

    sourceStarted = millis();
    nextScanTime = sourceStarted;
    udpDestination.fromString(UDP_DESTINATION);
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(false);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD); // Placeholders intentionally join simulation.
    nextWifiRetry = millis() + WIFI_RETRY_MS;
    server.begin();
    addEvent("Startup live; awaiting a complete valid frame");
}

void loop() {
    // Local alarms precede and follow each best-effort operation.
    // HTTP parsing, memory, socket lifetime, and write work have fixed bounds.
    // ADC, WiFi, UDP, tone and core internals can still introduce latency:
    // this single cooperative loop is expressly NOT hard real-time.
    serviceAlarms();
    serviceScan();
    serviceAlarms();
    serviceSerial();
    serviceAlarms();
    serviceWifi();
    serviceAlarms();
    server.service();
    serviceAlarms();
    serviceUdp();
    serviceAlarms();
    yield();
}
