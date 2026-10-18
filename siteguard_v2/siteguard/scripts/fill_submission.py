#!/usr/bin/env python3
"""Fill docs/SUBMISSION_TEMPLATE.md from evidence/results.json -> docs/SUBMISSION_FINAL.md.
Drops bonus sections you are not claiming and refuses to finish if required values are empty."""
import json, re, sys, os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
res = json.load(open(f"{R}/evidence/results.json"))
t = open(f"{R}/docs/SUBMISSION_TEMPLATE.md").read()

def strip(t, tag, keep):
    pat = re.compile(rf"<!--{tag}_START-->\n?(.*?)<!--{tag}_END-->\n?", re.S)
    return pat.sub(lambda m: m.group(1) if keep else "", t)

for tag, key in (("EO", "edge_optimization"), ("CL", "closed_loop"), ("LI", "live_intelligence")):
    t = strip(t, tag, res.get(key))

bonuses = [n for n, k in (("Edge Optimization", "edge_optimization"), ("Closed Loop", "closed_loop"),
           ("Live Intelligence", "live_intelligence")) if res.get(k)]
res["bonuses"] = ", ".join(bonuses) or "none"
res["precisions"] = "FP16 and INT8" if res.get("edge_optimization") else "FP16"
extra = []
if res.get("closed_loop"): extra += ["FirmGen traceability report", "UART output"]
res["evidence_extra"] = (", " + ", ".join(extra)) if extra else ""

missing = []
def sub(m):
    v = res
    for p in m.group(1).split("."):
        v = v.get(p, "") if isinstance(v, dict) else ""
    if v in ("", None) and m.group(1) != "evidence_extra": missing.append(m.group(1))
    return str(v)
out = re.sub(r"\{\{([\w.]+)\}\}", sub, t)
open(f"{R}/docs/SUBMISSION_FINAL.md", "w").write(out)
if missing:
    print("STILL EMPTY in evidence/results.json:", ", ".join(sorted(set(missing)))); sys.exit(1)
print("OK -> docs/SUBMISSION_FINAL.md (paste into the form)")
