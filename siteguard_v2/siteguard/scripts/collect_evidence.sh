#!/usr/bin/env bash
# Run once at the end: snapshots versions and hardware info into evidence/.
cd "$(dirname "$0")/.."
mkdir -p evidence
{ echo "== date"; date; echo "== pipegen"; pipegen --version 2>&1;
  echo "== gpu"; nvidia-smi 2>&1 | head -15; echo "== os"; uname -a; } > evidence/environment.txt
cp -n alerts/../evidence/incident_log.jsonl evidence/incident_sample.json 2>/dev/null || true
echo "Saved evidence/environment.txt. Still add by hand: pipeline_ir_graph.png, tensorrt_speed_report.png, demo/demo.mp4"
ls -la evidence
