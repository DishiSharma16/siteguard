# SiteGuard: A Physical AI Safety Sentinel That Sees, Decides, and Acts

**Team:** {{team}}

**Problem.** Workers enter hazard zones near machinery, forklifts, or open edges and nobody notices until an incident. Watching cameras does not scale, and plain motion alarms fire constantly.

**Track.** Track A (PipeGen), Suggested Track 1 (Workplace Safety Sentinel). Bonuses: {{bonuses}}.

## PipeGen pipeline (all five stages: Requirement, Pipeline IR, Model, Compiler, Run)
- **Requirement:** {{requirement_sentence}}
- **Input:** USB camera, live (recorded video as fallback)
- **Tasks:** person detection, multi-object tracking with stable IDs, hazard-zone intrusion with a {{dwell_seconds}} s dwell filter
- **Model:** {{model_name}}, ONNX compiled to a TensorRT engine ({{precisions}})
- **Outputs:** live overlay with zone, JSON metadata, MQTT alerts on `siteguard/alerts`, JSON incident log, {{extra_outputs}}

**Why PipeGen is load-bearing.** The detector, tracker, TensorRT engines and DeepStream application were generated, compiled and benchmarked by PipeGen. Our alert engine (zone polygon, dwell time, ALERT/CLEAR state machine, MQTT schema, incident log) consumes PipeGen's output feed. Without PipeGen there is no product.

<!--EO_START-->
## Edge Optimization (from PipeGen reports)
| Precision | FPS | Latency (ms) | Power (W) | Accuracy vs FP16 |
|---|---|---|---|---|
| FP16 | {{fp16.fps}} | {{fp16.latency_ms}} | {{fp16.power_w}} | baseline |
| INT8 | {{int8.fps}} | {{int8.latency_ms}} | {{int8.power_w}} | {{int8.accuracy}} |

**Trade-off:** {{tradeoff_sentence}}
<!--EO_END-->

<!--CL_START-->
## Closed Loop
An ESP32, with firmware built by FirmGen from a reviewed and frozen PRD (REQ-01 to REQ-09), subscribes to `siteguard/alerts`. On ALERT it turns on a red LED and buzzer; on CLEAR it turns them off. The vision-to-board bridge is itself a PRD requirement. Measured end-to-end latency from alert publish to actuation: {{e2e_latency_ms}} ms.
<!--CL_END-->

<!--LI_START-->
## Live Intelligence
FirmGen telemetry is enabled; heap, tasks, queue depth and the last received state are shown live during the demo.
<!--LI_END-->

## Evidence
Pipeline IR node graph, TensorRT speed report, MQTT log, incident JSON, demo video{{evidence_extra}}.
