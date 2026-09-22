"""Turn the CSVs in docs/results/ into the summary table for docs/RESULTS.md.

Usage: python3 bench/summarize.py [docs/results/*.csv]  |  task summarize
One row per (backend, mode, rps step): backend cpu cores avg, backend working
set max, achieved rps, disk write MB/s and busy fraction on the backend vms, fluent-bit
retries and errors, disk delta.
"""

import csv
import glob
import sys
from collections import defaultdict

files = sys.argv[1:] or sorted(glob.glob("docs/results/*.csv"))
rows = defaultdict(dict)  # (backend, mode, step) -> {metric: value}
containers = defaultdict(dict)  # (backend, mode, step) -> {name: (cpu, mem)}

for f in files:
    with open(f) as fh:
        for r in csv.DictReader(fh):
            key = (r["backend"], r["mode"], int(r["rps_per_traefik"]))
            comp, metric, value = r["component"], r["metric"], float(r["value"])
            if comp == "backend":
                rows[key][metric] = value
            elif metric == "host_disk_busy":
                rows[key]["busy"] = max(rows[key].get("busy", 0), value)
            elif metric == "host_write_bytes_ps":
                rows[key]["host_w"] = rows[key].get("host_w", 0) + value
            elif metric in ("disk_write_bytes_ps", "disk_read_bytes_ps"):
                pass
            elif comp == "traefik" and metric == "rps_achieved":
                rows[key]["rps"] = value
            elif comp == "fluent-bit":
                rows[key][metric] = value
            elif metric == "disk_delta_bytes":
                rows[key]["disk"] = rows[key].get("disk", 0) + value
            elif metric in ("cpu_cores_avg", "mem_ws_max_bytes"):
                # cluster stacks run the same container name on several vms:
                # cpu arrives already summed by name, memory as one row per vm
                c = containers[key].setdefault(comp, {"n": 0})
                if metric == "mem_ws_max_bytes":
                    c["n"] += 1
                    c[metric] = max(c.get(metric, 0), value)
                else:
                    c[metric] = value


def gib(b):
    return f"{b / 2**30:.2f} GiB"


print("| backend | mode | rps/traefik | rps achieved | backend cpu cores | backend mem max | disk write | disk busy max | retries | errors | disk growth | per container (cpu / mem) |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|")
for key in sorted(rows):
    r = rows[key]
    per = ", ".join(
        f"{n}{' x' + str(v['n']) if v['n'] > 1 else ''} {v.get('cpu_cores_avg', 0):.2f} / {gib(v.get('mem_ws_max_bytes', 0))}"
        + (" each" if v["n"] > 1 else "")
        for n, v in sorted(containers[key].items())
    )
    print(
        f"| {key[0]} | {key[1]} | {key[2]} | {r.get('rps', 0):.0f} | {r.get('cpu_cores_avg', 0):.2f} "
        f"| {gib(r.get('mem_ws_max_bytes', 0))} | {r.get('host_w', 0) / 2**20:.1f} MB/s | {r.get('busy', 0) * 100:.0f}% "
        f"| {r.get('retries', 0):.0f} | {r.get('errors', 0):.0f} "
        f"| {gib(-r.get('disk', 0))} | {per} |"
    )
