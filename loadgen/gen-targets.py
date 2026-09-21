"""Generate the vegeta target files for the bench.

Usage: python3 loadgen/gen-targets.py   (rewrites loadgen/targets/traefik-*.txt)

vegeta walks the file top to bottom and wraps around, so the share of every
request type is simply how many lines it gets. The mix, per 1000 requests:
roughly 2.5% 5xx (500/503 from api, 502 from the dead legacy backend), 6% 4xx
(404, 401, 403, unknown host), 1% slow (1s delay), 15% POST.
"""

import random
from pathlib import Path

TARGETS = ["traefik-1", "traefik-2"]
LINES = 1000
OUT = Path(__file__).parent / "targets"

AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "python-requests/2.32.3",
    "curl/8.7.1",
    "Go-http-client/2.0",
]

# (weight, host, method, path template, body file or None)
MIX = [
    (220, "api.bench", "GET", "/anything/users/{id}", None),
    (120, "api.bench", "GET", "/anything/products?page={page}&sort=price", None),
    (60, "api.bench", "GET", "/json", None),
    (60, "api.bench", "POST", "/anything/orders", "order.json"),
    (12, "api.bench", "GET", "/status/500", None),
    (6, "api.bench", "GET", "/status/503", None),
    (10, "api.bench", "GET", "/delay/1", None),
    (150, "shop.bench", "GET", "/anything/cart/{id}", None),
    (60, "shop.bench", "GET", "/bytes/2048", None),
    (40, "shop.bench", "POST", "/anything/cart/{id}/items", "item.json"),
    (25, "shop.bench", "GET", "/status/404", None),
    (50, "auth.bench", "POST", "/anything/login", "login.json"),
    (40, "auth.bench", "GET", "/anything/session/{id}", None),
    (15, "auth.bench", "GET", "/status/401", None),
    (10, "auth.bench", "GET", "/status/403", None),
    (90, "static.bench", "GET", "/", None),
    (10, "static.bench", "GET", "/assets/app.{id}.js", None),
    (7, "legacy.bench", "GET", "/v1/report", None),
    (10, "nobody.bench", "GET", "/", None),
    (5, "static.bench", "GET", "/health", None),
]

BODIES = {
    "order.json": '{"user_id": 4211, "items": [{"sku": "A-1001", "qty": 2}, {"sku": "B-2002", "qty": 1}], "coupon": null}',
    "item.json": '{"sku": "C-3003", "qty": 1}',
    "login.json": '{"username": "user4211", "password": "hunter2", "remember": true}',
}


def main():
    rng = random.Random(42)
    weights = [m[0] for m in MIX]
    total = sum(weights)
    picks = []
    for m in MIX:
        picks += [m] * round(m[0] / total * LINES)
    rng.shuffle(picks)

    for name, body in BODIES.items():
        (OUT / name).write_text(body + "\n")

    for target in TARGETS:
        lines = []
        for _, host, method, path, body in picks:
            path = path.format(id=rng.randint(1, 5000), page=rng.randint(1, 40))
            lines.append(f"{method} http://{target}{path}")
            lines.append(f"Host: {host}")
            lines.append(f"User-Agent: {rng.choice(AGENTS)}")
            lines.append("Accept: application/json, text/plain, */*")
            if body:
                lines.append("Content-Type: application/json")
                lines.append(f"@/targets/{body}")
            lines.append("")
        (OUT / f"{target}.txt").write_text("\n".join(lines))
        print(f"{target}: {len(picks)} targets")


if __name__ == "__main__":
    main()
