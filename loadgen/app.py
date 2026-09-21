"""RPS control page for the bench.

vegeta fixes the rate per process, so "set RPS" means: kill the running
attack for that target and start a new one. Rate 0 stops it.

  GET  /            html form + status
  GET  /status      json {"traefik-1": {"rate": 500, "pid": 42, "since": ...}, ...}
  POST /set         form: target=traefik-1&rate=500
  POST /stop        form: target=traefik-1 (or target=all)
"""

import html
import json
import os
import signal
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

TARGETS_DIR = os.environ.get("TARGETS_DIR", "/targets")
TARGETS = sorted(f[:-4] for f in os.listdir(TARGETS_DIR) if f.endswith(".txt"))
MAX_RATE = int(os.environ.get("MAX_RATE", "10000"))

attacks = {}  # target -> {"proc": Popen, "rate": int, "since": float}


def stop(target):
    a = attacks.pop(target, None)
    if a is None:
        return
    a["proc"].send_signal(signal.SIGINT)
    try:
        a["proc"].wait(timeout=10)
    except subprocess.TimeoutExpired:
        a["proc"].kill()


def start(target, rate):
    stop(target)
    if rate <= 0:
        return
    cmd = [
        "vegeta", "attack",
        f"-targets={TARGETS_DIR}/{target}.txt",
        f"-rate={rate}/1s",
        "-duration=0",
        "-workers=16",
        "-max-workers=256",
        "-timeout=5s",
        "-keepalive=true",
        "-output=/dev/null",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    attacks[target] = {"proc": proc, "rate": rate, "since": time.time()}


def status():
    out = {}
    for t in TARGETS:
        a = attacks.get(t)
        if a is None:
            out[t] = {"rate": 0, "pid": None, "since": None, "alive": False}
            continue
        alive = a["proc"].poll() is None
        out[t] = {"rate": a["rate"], "pid": a["proc"].pid, "since": int(a["since"]), "alive": alive}
        if not alive:
            out[t]["exit_code"] = a["proc"].returncode
            out[t]["stderr"] = a["proc"].stderr.read().decode(errors="replace")[-500:]
    return out


def page():
    rows = []
    for t, s in status().items():
        state = "running" if s["alive"] else ("stopped" if s["pid"] is None else f"exited {s.get('exit_code')}")
        uptime = f"{int(time.time() - s['since'])}s" if s["alive"] else "-"
        rows.append(
            f"<tr><td>{html.escape(t)}</td><td>{s['rate']}</td><td>{state}</td><td>{uptime}</td>"
            f"<td><form method=post action=/set><input type=hidden name=target value='{t}'>"
            f"<input type=number name=rate min=0 max={MAX_RATE} value='{s['rate']}' size=6> rps "
            f"<button>set</button></form></td>"
            f"<td><form method=post action=/stop><input type=hidden name=target value='{t}'>"
            f"<button>stop</button></form></td></tr>"
        )
    return f"""<!doctype html>
<html><head><meta charset=utf-8><title>traefik-logging loadgen</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; }}
table {{ border-collapse: collapse; }}
td, th {{ border: 1px solid #999; padding: .4rem .8rem; text-align: left; }}
form {{ display: inline; }}
</style></head><body>
<h1>loadgen</h1>
<p>Constant-rate GET / against each traefik via vegeta. Rate 0 stops the attack.</p>
<table>
<tr><th>target</th><th>rate</th><th>state</th><th>uptime</th><th>set</th><th></th></tr>
{''.join(rows)}
</table>
<p><form method=post action=/stop><input type=hidden name=target value=all><button>stop all</button></form>
<a href=/status>status json</a></p>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self):
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def _form(self):
        length = int(self.headers.get("Content-Length", "0"))
        return {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode()).items()}

    def do_GET(self):
        if self.path == "/status":
            self._send(200, json.dumps(status(), indent=2), "application/json")
        elif self.path == "/":
            self._send(200, page())
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self):
        form = self._form()
        target = form.get("target", "")
        if self.path == "/set":
            if target not in TARGETS:
                return self._send(400, "unknown target", "text/plain")
            try:
                rate = max(0, min(MAX_RATE, int(form.get("rate", "0"))))
            except ValueError:
                return self._send(400, "rate must be an integer", "text/plain")
            start(target, rate)
        elif self.path == "/stop":
            for t in (TARGETS if target == "all" else [target]):
                stop(t)
        else:
            return self._send(404, "not found", "text/plain")
        if "application/json" in self.headers.get("Accept", ""):
            return self._send(200, json.dumps(status()), "application/json")
        self._redirect()

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}")


if __name__ == "__main__":
    print(f"targets: {TARGETS}")
    server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
    try:
        server.serve_forever()
    finally:
        for t in list(attacks):
            stop(t)
