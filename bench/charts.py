"""Comparison charts from docs/results/*.csv.

Usage: python3 bench/charts.py   |  task charts
Writes docs/charts/<metric>-<mode>.svg (light theme, for README/RESULTS on
github) and docs/charts.html (both themes, hover tooltips, the table).

Points that came out of a broken step are dropped here by hand (see SKIP),
the csv keeps them. Storage per line is typed in from the run notes in
RESULTS.md, it is not in the csv.
"""

import csv
import glob
import html
from collections import defaultdict

STEPS = [100, 500, 1000, 2000]
FAMILIES = [("victorialogs", "VictoriaLogs"), ("loki", "Loki"), ("elk", "ELK"), ("openobserve", "OpenObserve")]
COLOR = {"victorialogs": ("#2a78d6", "#3987e5"), "loki": ("#eb6834", "#d95926"),
         "elk": ("#1baf7a", "#199e70"), "openobserve": ("#eda100", "#c98500")}
# (backend, mode, step): the step ran into the host stall, the number is not a measurement
SKIP = {("loki", "cluster", 1000)}
# (backend, mode, step) measured, but the step was cut short
PARTIAL = {("elk", "single", 2000): "11 of 15 minutes, disk-bound"}
METRICS = [("cpu", "CPU, cores", "cores"), ("mem", "Memory, GiB", "GiB"), ("disk", "Disk writes, MB/s", "MB/s")]
# bytes per stored line, on disk incl. wal/cache; parquet/index only in the note
STORAGE = [
    ("victorialogs", "single", 286 / 6.55, ""),
    ("victorialogs", "cluster", 307 / 6.55, "3 storage nodes, 1 copy"),
    ("loki", "single", 465 / 6.55, "chunks + tsdb index + wal"),
    ("elk", "single", 897 / 5.53, "keyword index + _source"),
    ("openobserve", "single", 760 / 10.1, "339 MB parquet of that: 34 B/line"),
    ("openobserve", "cluster", 970 / 6.55, "364 MB parquet in minio: 56 B/line"),
]


def load():
    rows = defaultdict(dict)
    for f in sorted(glob.glob("docs/results/*.csv")):
        with open(f) as fh:
            for r in csv.DictReader(fh):
                key = (r["backend"], r["mode"], int(r["rps_per_traefik"]))
                comp, m, v = r["component"], r["metric"], float(r["value"])
                if comp == "backend" and m == "cpu_cores_avg":
                    rows[key]["cpu"] = v
                elif comp == "backend" and m == "mem_ws_max_bytes":
                    rows[key]["mem"] = v / 2**30
                elif m == "host_write_bytes_ps":
                    rows[key]["disk"] = rows[key].get("disk", 0) + v / 2**20
                elif comp == "traefik" and m == "rps_achieved":
                    rows[key]["rps"] = v
    return {k: v for k, v in rows.items() if k[2] in STEPS and k not in SKIP}


def nice_max(v):
    for m in (0.5, 1, 2, 3, 4, 5, 6, 8, 10):
        if v <= m:
            return m
    return v


def line_chart(data, metric, mode, unit, themed):
    """One panel: x = rps step, one line per backend family present in this mode."""
    W, H, L, R, T, B = 360, 230, 44, 96, 18, 34
    pw, ph = W - L - R, H - T - B
    series = []
    for fam, label in FAMILIES:
        pts = [(s, data[(fam, mode, s)][metric], (fam, mode, s)) for s in STEPS if (fam, mode, s) in data and metric in data[(fam, mode, s)]]
        if pts:
            series.append((fam, label, pts))
    ymax = nice_max(max(p[1] for _, _, pts in series for p in pts) * 1.05)
    xs = {s: L + i * pw / (len(STEPS) - 1) for i, s in enumerate(STEPS)}
    y = lambda v: T + ph - v / ymax * ph
    ink = 'class="ink"' if themed else 'fill="#52514e"'
    grid = 'class="grid"' if themed else 'stroke="#e1e0d9"'
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="system-ui,-apple-system,Segoe UI,sans-serif" font-size="11">']
    if not themed:
        out.append(f'<rect width="{W}" height="{H}" fill="#fcfcfb"/>')
    ticks = 4
    for i in range(ticks + 1):
        v = ymax * i / ticks
        out.append(f'<line x1="{L}" x2="{L+pw}" y1="{y(v):.1f}" y2="{y(v):.1f}" {grid} stroke-width="1"/>')
        out.append(f'<text x="{L-6}" y="{y(v)+4:.1f}" text-anchor="end" {ink}>{v:g}</text>')
    for s in STEPS:
        out.append(f'<text x="{xs[s]:.1f}" y="{H-12}" text-anchor="middle" {ink}>{s}</text>')
    out.append(f'<text x="{L+pw/2:.1f}" y="{H-1}" text-anchor="middle" {ink} font-size="10">rps per traefik</text>')
    out.append(f'<text x="{L-6}" y="{T-6}" text-anchor="end" {ink} font-size="10">{unit}</text>')
    # end labels: sort by final y and push apart
    ends = []
    for fam, label, pts in series:
        color = COLOR[fam][0]
        stroke = f'class="s-{fam}"' if themed else f'stroke="{color}"'
        d = " ".join(f"{'M' if i == 0 else 'L'}{xs[s]:.1f},{y(v):.1f}" for i, (s, v, _) in enumerate(pts))
        out.append(f'<path d="{d}" fill="none" {stroke} stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
        for s, v, key in pts:
            partial = key in PARTIAL
            fill = f'class="f-{fam}"' if themed else f'fill="{color}"'
            ring = 'class="ring"' if themed else 'stroke="#fcfcfb"'
            title = f"{label} {mode}, {s} rps/traefik: {v:.2f} {unit}" + (f" ({PARTIAL[key]})" if partial else "")
            if partial:
                out.append(f'<circle cx="{xs[s]:.1f}" cy="{y(v):.1f}" r="4.5" fill="none" {stroke} stroke-width="2"><title>{html.escape(title)}</title></circle>')
            else:
                out.append(f'<circle cx="{xs[s]:.1f}" cy="{y(v):.1f}" r="4.5" {fill} {ring} stroke-width="2"><title>{html.escape(title)}</title></circle>')
        s, v, _ = pts[-1]
        ends.append([y(v), xs[s], f"{label} {v:.2f}", fam])
    ends.sort()
    for i in range(1, len(ends)):
        if ends[i][0] - ends[i-1][0] < 13:
            ends[i][0] = ends[i-1][0] + 13
    for ey, ex, text, fam in ends:
        out.append(f'<text x="{ex+8:.1f}" y="{ey+4:.1f}" {ink} font-size="10.5">{html.escape(text)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def bar_chart(themed):
    W, BH, L, R, T = 560, 22, 150, 70, 14
    items = sorted(STORAGE, key=lambda t: t[2])
    H = T + len(items) * (BH + 8) + 26
    pw = W - L - R
    vmax = 200
    ink = 'class="ink"' if themed else 'fill="#52514e"'
    grid = 'class="grid"' if themed else 'stroke="#e1e0d9"'
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="system-ui,-apple-system,Segoe UI,sans-serif" font-size="11">']
    if not themed:
        out.append(f'<rect width="{W}" height="{H}" fill="#fcfcfb"/>')
    for v in (0, 50, 100, 150, 200):
        x = L + v / vmax * pw
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{T}" y2="{H-24}" {grid} stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{H-8}" text-anchor="middle" {ink}>{v}</text>')
    labels = dict(FAMILIES)
    for i, (fam, mode, v, note) in enumerate(items):
        yy = T + i * (BH + 8)
        w = v / vmax * pw
        fill = f'class="f-{fam}"' if themed else f'fill="{COLOR[fam][0]}"'
        title = f"{labels[fam]} {mode}: {v:.0f} bytes per line on disk" + (f" ({note})" if note else "")
        out.append(f'<path d="M{L},{yy} h{w-4:.1f} a4,4 0 0 1 4,4 v{BH-8} a4,4 0 0 1 -4,4 h-{w-4:.1f} z" {fill}><title>{html.escape(title)}</title></path>')
        out.append(f'<text x="{L-8}" y="{yy+BH/2+4:.1f}" text-anchor="end" {ink}>{labels[fam]} {mode}</text>')
        out.append(f'<text x="{L+w+6:.1f}" y="{yy+BH/2+4:.1f}" {ink}>{v:.0f} B</text>')
    out.append(f'<text x="{L+pw/2:.1f}" y="{H-8+0:.1f}" {ink} font-size="10" text-anchor="middle" dy="0"></text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    data = load()
    for metric, title, unit in METRICS:
        for mode in ("single", "cluster"):
            with open(f"docs/charts/{metric}-{mode}.svg", "w") as f:
                f.write(line_chart(data, metric, mode, unit, themed=False))
    with open("docs/charts/storage.svg", "w") as f:
        f.write(bar_chart(themed=False))

    panels = []
    for mode in ("single", "cluster"):
        cells = "".join(f'<figure><figcaption>{t}</figcaption>{line_chart(data, m, mode, u, themed=True)}</figure>' for m, t, u in METRICS)
        panels.append(f'<section class="row"><h2>{mode}</h2><div class="grid3">{cells}</div></section>')
    labels = dict(FAMILIES)
    trs = []
    for (fam, mode, step), r in sorted(data.items(), key=lambda kv: (kv[0][1], kv[0][0], kv[0][2])):
        note = PARTIAL.get((fam, mode, step), "")
        trs.append(f"<tr><td>{labels[fam]}</td><td>{mode}</td><td>{step}</td><td>{r.get('rps',0):.0f}</td><td>{r.get('cpu',0):.2f}</td><td>{r.get('mem',0):.2f}</td><td>{r.get('disk',0):.1f}</td><td>{html.escape(note)}</td></tr>")
    legend = "".join(f'<span class="key"><i class="f-{fam}"></i>{label}</span>' for fam, label in FAMILIES)
    page = f'''<title>Traefik log backends</title>
<meta name="description" content="cpu, memory and disk of victorialogs, loki, elasticsearch and openobserve fed with traefik access logs at 100 to 2000 rps per traefik">
<style>
:root {{ --surface:#fcfcfb; --page:#f9f9f7; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --grid:#e1e0d9; --line:#c3c2b7;
  --victorialogs:#2a78d6; --loki:#eb6834; --elk:#1baf7a; --openobserve:#eda100; color-scheme: light; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --surface:#1a1a19; --page:#0d0d0d; --ink:#ffffff; --ink2:#c3c2b7; --muted:#898781; --grid:#2c2c2a; --line:#383835;
  --victorialogs:#3987e5; --loki:#d95926; --elk:#199e70; --openobserve:#c98500; color-scheme: dark; }} }}
:root[data-theme="dark"] {{ --surface:#1a1a19; --page:#0d0d0d; --ink:#ffffff; --ink2:#c3c2b7; --muted:#898781; --grid:#2c2c2a; --line:#383835;
  --victorialogs:#3987e5; --loki:#d95926; --elk:#199e70; --openobserve:#c98500; color-scheme: dark; }}
body {{ background: var(--page); color: var(--ink); font-family: system-ui, -apple-system, "Segoe UI", sans-serif; padding-inline: 16px; padding-block: 24px 48px; max-width: 1180px; margin-inline: auto; line-height: 1.45; }}
h1 {{ font-size: 1.6rem; margin: 0 0 4px; text-wrap: balance; }}
h2 {{ font-size: 0.85rem; text-transform: uppercase; letter-spacing: .06em; color: var(--ink2); margin: 28px 0 8px; }}
p {{ max-width: 68ch; color: var(--ink2); margin: 0 0 8px; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 14px; margin: 12px 0 4px; font-size: .9rem; }}
.key i {{ display: inline-block; width: 14px; height: 14px; border-radius: 3px; vertical-align: -2px; margin-right: 6px; }}
.grid3 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }}
figure {{ margin: 0; background: var(--surface); border: 1px solid var(--grid); border-radius: 6px; padding: 10px 8px 6px; }}
figcaption {{ font-size: .85rem; color: var(--ink2); margin: 0 0 4px 10px; }}
figure svg {{ width: 100%; height: auto; display: block; }}
.ink {{ fill: var(--ink2); }} .grid {{ stroke: var(--grid); }} .ring {{ stroke: var(--surface); }}
.s-victorialogs {{ stroke: var(--victorialogs); }} .f-victorialogs {{ fill: var(--victorialogs); background: var(--victorialogs); }}
.s-loki {{ stroke: var(--loki); }} .f-loki {{ fill: var(--loki); background: var(--loki); }}
.s-elk {{ stroke: var(--elk); }} .f-elk {{ fill: var(--elk); background: var(--elk); }}
.s-openobserve {{ stroke: var(--openobserve); }} .f-openobserve {{ fill: var(--openobserve); background: var(--openobserve); }}
circle {{ cursor: default; }}
.wide {{ overflow-x: auto; }}
table {{ border-collapse: collapse; font-size: .85rem; font-variant-numeric: tabular-nums; width: 100%; min-width: 620px; }}
th, td {{ text-align: left; padding: 5px 10px; border-bottom: 1px solid var(--grid); }}
td:nth-child(n+3), th:nth-child(n+3) {{ text-align: right; }} td:last-child, th:last-child {{ text-align: left; color: var(--ink2); }}
.note {{ font-size: .85rem; color: var(--muted); }}
</style>
<h1>Traefik log backends</h1>
<p>Two traefiks ship their access logs through fluent-bit into one backend at a time; both traefiks are loaded at the same rate, so 2000 rps per traefik is 4000 log lines a second (~6.4 MB/s of json). Each point is the average over minutes 2–15 of a 15 minute step; memory is the peak working set of every container in the backend stack (grafana counts for loki, kibana for elk, minio/nats/postgres for the clusters).</p>
<div class="legend">{legend}</div>
<p class="note">Hollow marker: step cut short. Loki cluster stops at 500 rps: its 1000 and 2000 rps steps ran into a host stall (host swap, since fixed) and are not measurements. Hover a point for the exact value.</p>
{"".join(panels)}
<section><h2>Bytes per stored line, on disk</h2>
<p>What one access line of ~1.6 KB became on the backend's disk after a full run, wal and caches included. Loki cluster has no complete run.</p>
<figure>{bar_chart(themed=True)}</figure></section>
<section><h2>All measured steps</h2>
<div class="wide"><table><thead><tr><th>backend</th><th>mode</th><th>rps/traefik</th><th>rps achieved</th><th>cpu cores</th><th>mem GiB</th><th>disk MB/s</th><th></th></tr></thead><tbody>{"".join(trs)}</tbody></table></div></section>
<p class="note">Source: <a href="https://github.com/m1xxos/traefik-logging">github.com/m1xxos/traefik-logging</a>, docs/results/*.csv and docs/RESULTS.md.</p>
'''
    with open("docs/charts.html", "w") as f:
        f.write(page)
    print("charts:", len(METRICS) * 2 + 1, "svg +", "docs/charts.html")


if __name__ == "__main__":
    main()
