#!/usr/bin/env python3
"""
SiteGuard alert engine: zone intrusion + dwell filter -> MQTT ALERT/CLEAR + JSON incident log.

Input: JSON-lines of per-frame detections (one JSON object per line), from a file PipeGen
writes, from stdin, or from --simulate. ADAPT config.json "input_adapter" to match the
real keys in PipeGen's JSON output (check one line of it first).

Examples:
  python3 zone_dwell.py --simulate                 # no PipeGen, no broker needed (prints)
  python3 zone_dwell.py --simulate --mqtt          # publish to local Mosquitto
  tail -F /path/to/pipegen/metadata.jsonl | python3 zone_dwell.py --stdin --mqtt
"""
import argparse, json, os, sys, time, datetime

HERE = os.path.dirname(os.path.abspath(__file__))


def load_cfg(path):
    with open(path) as f:
        return json.load(f)


def first_key(d, keys, default=None):
    for k in keys:
        if k in d:
            return d[k]
    return default


def point_in_poly(x, y, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def parse_frame(obj, cfg):
    """Return (frame_id, [(track_id, class, conf, (x1,y1,x2,y2)), ...])."""
    a = cfg["input_adapter"]
    objs = first_key(obj, a["objects_keys"], [])
    out = []
    for o in objs:
        cls = first_key(o, a["class_keys"], "")
        tid = first_key(o, a["id_keys"], -1)
        conf = float(first_key(o, a["conf_keys"], 1.0))
        bb = o.get(a["bbox_key"])
        if bb is None or len(bb) != 4:
            continue
        if a["bbox_format"] == "ltwh":
            x1, y1, w, h = bb
            bb = (x1, y1, x1 + w, y1 + h)
        out.append((tid, str(cls), conf, tuple(bb)))
    return obj.get("frame_id", obj.get("frame_num", -1)), out


class Engine:
    def __init__(self, cfg, publish):
        self.cfg = cfg
        W, H = cfg["frame"]["width"], cfg["frame"]["height"]
        self.poly = [(x * W, y * H) for x, y in cfg["zone_polygon_norm"]]
        self.first_in = {}      # track_id -> time first seen inside
        self.alerted = set()    # track_ids that crossed dwell threshold
        self.state = "CLEAR"
        self.last_inside = None
        self.event_n = 0
        self.publish = publish
        log = os.path.join(HERE, cfg["incident_log"])
        os.makedirs(os.path.dirname(log), exist_ok=True)
        self.log = open(log, "a")

    def emit(self, state, track_id, dwell, conf, frame_id, now):
        self.event_n += 1
        msg = {
            "event_id": f"evt_{self.event_n:06d}",
            "type": "ZONE_INTRUSION",
            "state": state,
            "zone_id": self.cfg["zone_id"],
            "track_id": track_id,
            "dwell_seconds": round(dwell, 2),
            "confidence": round(conf, 3),
            "timestamp": datetime.datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "ts_ms": int(now * 1000),   # for end-to-end latency measurement on the ESP32 side
            "frame_id": frame_id,
        }
        s = json.dumps(msg)
        self.publish(s)
        self.log.write(s + "\n")
        self.log.flush()
        print(s, flush=True)

    def step(self, frame_id, dets, now):
        c = self.cfg
        inside_now = {}
        for tid, cls, conf, (x1, y1, x2, y2) in dets:
            if cls != c["target_class"] or conf < c["min_confidence"]:
                continue
            foot = ((x1 + x2) / 2.0, y2)  # bottom-centre = where the person stands
            if point_in_poly(foot[0], foot[1], self.poly):
                inside_now[tid] = conf
        # drop tracks that left the zone
        for tid in list(self.first_in):
            if tid not in inside_now:
                del self.first_in[tid]
                self.alerted.discard(tid)
        for tid, conf in inside_now.items():
            self.first_in.setdefault(tid, now)
            dwell = now - self.first_in[tid]
            if dwell >= c["dwell_seconds"] and tid not in self.alerted:
                self.alerted.add(tid)
                self.state = "ALERT"
                self.emit("ALERT", tid, dwell, conf, frame_id, now)
        if inside_now:
            self.last_inside = now
        elif self.state == "ALERT" and self.last_inside is not None \
                and now - self.last_inside >= c["clear_seconds"]:
            self.state = "CLEAR"
            self.emit("CLEAR", -1, 0.0, 0.0, frame_id, now)


def simulate(cfg, fps=10):
    """Person walks past the zone (no alert), then walks in and stays (alert), then leaves (clear)."""
    W, H = cfg["frame"]["width"], cfg["frame"]["height"]
    def det(x, y, f):
        return {"frame_id": f, "objects": [{"track_id": 7, "class": "person", "confidence": 0.9,
                "bbox": [x - 40, y - 160, x + 40, y]}]}
    f = 0
    # 1) pass-through: crosses zone in 0.8 s -> must NOT alert
    for i in range(8):
        yield det(0.50 * W + i * 0.04 * W, 0.8 * H, f); f += 1
    for _ in range(15): yield {"frame_id": f, "objects": []}; f += 1
    # 2) intrusion: stand inside for 5 s -> ALERT after dwell
    for _ in range(50): yield det(0.75 * W, 0.8 * H, f); f += 1
    # 3) leave -> CLEAR after clear_seconds
    for _ in range(40): yield {"frame_id": f, "objects": []}; f += 1


def make_publisher(cfg, use_mqtt):
    if not use_mqtt:
        return lambda s: None
    import paho.mqtt.client as mqtt
    try:
        cl = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)   # paho-mqtt >= 2
    except AttributeError:
        cl = mqtt.Client()                                   # paho-mqtt 1.x
    cl.connect(cfg["mqtt"]["host"], cfg["mqtt"]["port"])
    cl.loop_start()
    return lambda s: cl.publish(cfg["mqtt"]["topic"], s, qos=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(HERE, "config.json"))
    ap.add_argument("--simulate", action="store_true")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--file")
    ap.add_argument("--mqtt", action="store_true")
    a = ap.parse_args()
    cfg = load_cfg(a.config)
    eng = Engine(cfg, make_publisher(cfg, a.mqtt))

    if a.simulate:
        for obj in simulate(cfg):
            fid, dets = parse_frame(obj, cfg)
            eng.step(fid, dets, time.time())
            time.sleep(0.1)
        return
    src = sys.stdin if a.stdin else open(a.file)
    for line in src:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        fid, dets = parse_frame(obj, cfg)
        eng.step(fid, dets, time.time())


if __name__ == "__main__":
    main()
