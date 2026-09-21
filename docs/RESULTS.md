# Results

_Last updated: 2026-09-21_

Backend vms get 9 GiB in both modes (single: 1 x 9 GiB, cluster: 3.5 + 2.75 + 2.75). Numbers are
per step (rps per traefik, two traefiks, so lines/s is double), measured over minutes 2-15 of a
15 minute step. `backend` rows sum every container of the stack, including minio / nats /
postgres / kibana where the stack has them.

Traffic is the weighted mix from `loadgen/gen-targets.py` (api/shop/auth/static by Host, dead
legacy backend, unknown host, ~2.5% 5xx, ~6% 4xx, 1% slow, 15% POST); with `headers: keep` an
access line is ~1.6 KB, so 2000 rps per traefik is ~6.4 MB/s of raw log.

Copies of every log line kept: victorialogs 1x (sharded, no replication), openobserve 1x,
elasticsearch 2x (1 replica), loki 3x (replication_factor 3). The cluster comparison is partly a
comparison of durability.

| backend | mode | rps/traefik | rps achieved | backend cpu cores | backend mem max | retries | errors | disk growth | per container (cpu / mem) |
|---|---|---|---|---|---|---|---|---|---|
| victorialogs | single | 0 | 371 | 0.05 | 0.28 GiB | 0 | 0 | 0.01 GiB | victorialogs 0.05 / 0.28 GiB |
| victorialogs | single | 100 | 200 | 0.02 | 0.21 GiB | 0 | 0 | 0.01 GiB | victorialogs 0.02 / 0.21 GiB |
| victorialogs | single | 500 | 1000 | 0.10 | 0.24 GiB | 0 | 0 | 0.03 GiB | victorialogs 0.10 / 0.24 GiB |
| victorialogs | single | 1000 | 2000 | 0.18 | 0.27 GiB | 0 | 0 | 0.09 GiB | victorialogs 0.18 / 0.27 GiB |
| victorialogs | single | 2000 | 4000 | 0.35 | 0.36 GiB | 0 | 0 | 0.14 GiB | victorialogs 0.35 / 0.36 GiB |

`rps/traefik = 0` is the 10 minute drain after the last step: what the backend costs while it
digests its buffers and merges with no new input.

## Run notes

### victorialogs single, 2026-09-21

- 6 550 784 access lines stored for 6 590 599 shipped by fluent-bit; the difference is the smoke
  test that ran before the data volume was wiped. No loss, no retries at any step.
- Status mix as designed: 200 91.5%, 404 3.5%, 401 1.5%, 403 1.0%, 500 1.2%, 502 0.7%, 503 0.6%.
- 286 MB on disk for ~10 GB of raw json lines (avg 1.6 KB): about 36x.
- At 2000 rps per traefik the traefik VMs sit at 70% cpu (traefik 0.9 cores, fluent-bit 0.45
  cores each) and loadgen at 0.75 cores. The backends are nowhere near the limit at this rate;
  the stand would need bigger traefik VMs to push further.

## Things that bite

- **Memory limits are cgroup limits.** A backend that hits `mem_limit` gets OOM-killed and
  restarts; check `container_last_seen` gaps before trusting a low RSS number.
- Loki `per_stream_rate_limit` is raised to 32MB; with the default 3MB/s a single host+service
  stream is throttled at ~1000 rps and the numbers only show the throttle.
- ELK needs `vm.max_map_count=1048576` (ansible sets it), and the cluster template writes 2 copies.
