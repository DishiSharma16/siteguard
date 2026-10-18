# PRD: SiteGuard Beacon (ESP32, ESP-IDF v5.5)

## 1. Purpose
A physical alarm node. It receives zone-intrusion alerts from the SiteGuard vision pipeline
(NVIDIA GPU / Jetson, PipeGen + DeepStream) over MQTT and drives a red LED and a buzzer.
This is the "act" half of a see-decide-act closed loop.

## 2. Hardware
- ESP32 dev board, USB cable (UART monitor at 115200)
- Red LED + resistor on GPIO 2 (GPIO_ALERT_LED)
- Active buzzer on GPIO 4 (GPIO_BUZZER)
- Green LED + resistor on GPIO 5 (GPIO_STATUS_LED)

## 3. Interface (bridge from PipeGen side)
- Wi-Fi: SSID/password from a Kconfig/menuconfig setting (not hardcoded in source)
- MQTT broker: host/port from Kconfig. Topic: `siteguard/alerts`, QoS 1
- Payload: JSON. Only the field `"state"` is required: `"ALERT"` or `"CLEAR"`.
  Optional `"ts_ms"` (sender epoch ms) and `"event_id"` are logged if present.
  Example: {"event_id":"evt_000123","state":"ALERT","zone_id":"hazard_zone_1","ts_ms":1760797930123}

## 4. Functional requirements
| ID | Requirement | Acceptance criterion |
|----|-------------|----------------------|
| REQ-01 | Connect to Wi-Fi at boot; retry with backoff until connected | UART shows "WIFI_CONNECTED ip=..." |
| REQ-02 | Connect to the MQTT broker and subscribe to `siteguard/alerts`; reconnect automatically | UART shows "MQTT_SUBSCRIBED topic=siteguard/alerts" |
| REQ-03 | On state=ALERT turn ON red LED and buzzer within 200 ms of message receipt | UART logs receive-time and actuate-time; delta < 200 ms; physical LED/buzzer on |
| REQ-04 | On state=CLEAR turn OFF red LED and buzzer | UART "STATE=CLEAR"; outputs off |
| REQ-05 | Ignore malformed JSON or unknown state; keep current outputs; log a warning | Publishing garbage does not change outputs; UART "WARN bad_payload" |
| REQ-06 | Status LED: solid = broker connected, blinking 2 Hz = disconnected | Stop broker -> status LED blinks; restart -> solid |
| REQ-07 | Fail-safe: if broker connection is lost while in ALERT, keep the alarm ON until a CLEAR arrives or 30 s pass | Verified by stopping broker during ALERT |
| REQ-08 | Log every received state change over UART with event_id and a monotonic uptime in ms | UART line per message |
| REQ-09 | Alert handling must not block the MQTT task (use an RTOS queue and a dedicated actuator task) | Design doc and unit test show queue between tasks |

## 5. Non-functional
- Boot to subscribed in under 15 s on a normal Wi-Fi network
- No hardcoded credentials in the repo
- Unit tests for the JSON state parser (valid ALERT, valid CLEAR, malformed, unknown state)

## 6. Live Intelligence (optional)
Enable FirmGen telemetry so the RTOS/System Monitor shows: heap free, task list, queue depth,
last received state, and uptime during the demo.

## 7. Out of scope
OTA, TLS, multiple zones, display.
