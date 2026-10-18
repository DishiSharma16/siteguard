#!/usr/bin/env bash
# One-command demo. Usage: PIPEGEN_JSON=/home/you/path/to/pipegen/json_output.jsonl ./scripts/run_demo.sh
# Starts broker, alert engine on PipeGen's JSON output, and an MQTT log. Start PipeGen separately:
#   (cd pipegen_export && ./run.sh)
set -e
cd "$(dirname "$0")/.."
: "${PIPEGEN_JSON:?set PIPEGEN_JSON to the JSON-lines file PipeGen writes}"
mkdir -p evidence
pgrep mosquitto >/dev/null || (mosquitto -c alerts/mosquitto.conf -d && sleep 1)
mosquitto_sub -t siteguard/alerts -v | tee -a evidence/mqtt_log.txt &
SUB=$!
trap "kill $SUB 2>/dev/null" EXIT
tail -n 0 -F "$PIPEGEN_JSON" | python3 alerts/zone_dwell.py --stdin --mqtt
