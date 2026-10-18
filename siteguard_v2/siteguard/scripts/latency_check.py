#!/usr/bin/env python3
"""Measures publish->receive latency of ALERT messages (run on the same machine as the alert engine,
or one with a synced clock). For ESP32 actuation latency use slow-motion video or the UART timestamps."""
import json, statistics, time, sys
import paho.mqtt.client as mqtt
host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
vals = []
def on_msg(c, u, m):
    try: d = json.loads(m.payload)
    except Exception: return
    if d.get("state") == "ALERT" and "ts_ms" in d:
        vals.append(time.time() * 1000 - d["ts_ms"])
        print(f"alert latency: {vals[-1]:.1f} ms  (median {statistics.median(vals):.1f} ms, n={len(vals)})", flush=True)
try: c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
except AttributeError: c = mqtt.Client()
c.on_message = on_msg
c.connect(host, 1883); c.subscribe("siteguard/alerts"); c.loop_forever()
