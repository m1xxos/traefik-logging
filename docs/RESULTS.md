# Results

_Last updated: 2026-09-22_

Backend vms get 9 GiB in both modes (single: 1 x 9 GiB, cluster: 3.5 + 2.75 + 2.75). Numbers are
per step (rps per traefik, two traefiks, so lines/s is double), measured over minutes 2-15 of a
15 minute step. `backend` rows sum every container of the stack, including minio / nats /
postgres / kibana where the stack has them, and grafana for loki (it has no ui of its own).

Traffic is the weighted mix from `loadgen/gen-targets.py` (api/shop/auth/static by Host, dead
legacy backend, unknown host, ~2.5% 5xx, ~6% 4xx, 1% slow, 15% POST); with `headers: keep` an
access line is ~1.6 KB, so 2000 rps per traefik is ~6.4 MB/s of raw log.

Copies of every log line kept: victorialogs 1x (sharded, no replication), openobserve 1x,
elasticsearch 2x (1 replica), loki 3x (replication_factor 3). The cluster comparison is partly a
comparison of durability.

| backend | mode | rps/traefik | rps achieved | backend cpu cores | backend mem max | retries | errors | disk growth | per container (cpu / mem) |
|---|---|---|---|---|---|---|---|---|---|
| loki | single | 0 | 286 | 0.07 | 0.84 GiB | 0 | 0 | -1.75 GiB | loki 0.06 / 0.53 GiB, loki-grafana 0.02 / 0.32 GiB |
| loki | single | 100 | 200 | 0.04 | 0.47 GiB | 0 | 0 | -0.01 GiB | loki 0.03 / 0.15 GiB, loki-grafana 0.01 / 0.32 GiB |
| loki | single | 500 | 1000 | 0.11 | 0.63 GiB | 0 | 0 | 0.26 GiB | loki 0.10 / 0.31 GiB, loki-grafana 0.01 / 0.32 GiB |
| loki | single | 1000 | 2000 | 0.21 | 0.77 GiB | 0 | 0 | 0.24 GiB | loki 0.20 / 0.45 GiB, loki-grafana 0.01 / 0.32 GiB |
| loki | single | 2000 | 4000 | 0.54 | 0.89 GiB | 0 | 0 | 0.52 GiB | loki 0.52 / 0.57 GiB, loki-grafana 0.01 / 0.32 GiB |
| victorialogs | cluster | 0 | 386 | 0.04 | 0.58 GiB | 0 | 0 | 0.01 GiB | vlinsert 0.01 / 0.08 GiB, vlselect 0.00 / 0.01 GiB, vlstorage x3 0.03 / 0.18 GiB each |
| victorialogs | cluster | 100 | 200 | 0.04 | 0.37 GiB | 0 | 0 | 0.01 GiB | vlinsert 0.01 / 0.02 GiB, vlselect 0.00 / 0.03 GiB, vlstorage x3 0.03 / 0.12 GiB each |
| victorialogs | cluster | 500 | 1000 | 0.09 | 0.45 GiB | 0 | 0 | 0.03 GiB | vlinsert 0.02 / 0.04 GiB, vlselect 0.00 / 0.01 GiB, vlstorage x3 0.07 / 0.15 GiB each |
| victorialogs | cluster | 1000 | 2000 | 0.15 | 0.60 GiB | 0 | 0 | 0.07 GiB | vlinsert 0.04 / 0.08 GiB, vlselect 0.00 / 0.01 GiB, vlstorage x3 0.11 / 0.19 GiB each |
| victorialogs | cluster | 2000 | 4000 | 0.30 | 0.65 GiB | 0 | 0 | 0.14 GiB | vlinsert 0.10 / 0.11 GiB, vlselect 0.00 / 0.01 GiB, vlstorage x3 0.20 / 0.21 GiB each |
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

### victorialogs cluster, 2026-09-22

- 6 551 147 access lines stored for 6 553 620 shipped; the 2.5k difference is the smoke test
  before the wipe. No loss, no retries.
- vlinsert shards evenly: 2 185 195 / 2 184 653 / 2 181 299 lines, ~102 MB per node, 307 MB in
  total (single node run: 286 MB). One copy of every line; losing a node loses a third of the
  data and makes queries fail with 502 until it is back.
- Cluster total is about the same cpu as single (0.30 vs 0.35 cores at 2000 rps) and roughly
  twice the memory (0.65 vs 0.36 GiB), the price of three storage processes plus vlinsert.
  vlselect idles without queries.
- Traefik VMs were 8 GiB for this run (2 GiB for the single run); traefik and fluent-bit never
  used more than ~200 MiB together, so it changes nothing in the numbers.

### loki single, 2026-09-22

- 6 550 804 access lines stored, `loki_discarded_samples_total` 0, no fluent-bit retries. 13
  streams (host x ServiceName, plus the internal log).
- 465 MB on disk (chunks + tsdb index + wal) for the same ~10 GB of raw lines: ~22x, against
  ~36x for victorialogs. The `disk growth` column is noisy for loki: the wal is written and
  freed as chunks flush, hence the negative drain value.
- loki itself: 0.52 cores / 0.57 GiB at 2000 rps (victorialogs: 0.35 / 0.36). loki-grafana adds
  a flat 0.01 cores / 0.32 GiB doing nothing but being up; it is in the `backend` total because
  loki has no ui without it.
- `per_stream_rate_limit` raised to 32MB was needed: the api@docker stream alone is ~1.7 MB/s
  per traefik at 2000 rps, well above the 3 MB/s default with burst.

## Things that bite

- **Memory limits are cgroup limits.** A backend that hits `mem_limit` gets OOM-killed and
  restarts; check `container_last_seen` gaps before trusting a low RSS number.
- Loki `per_stream_rate_limit` is raised to 32MB; with the default 3MB/s a single host+service
  stream is throttled at ~1000 rps and the numbers only show the throttle.
- ELK needs `vm.max_map_count=1048576` (ansible sets it), and the cluster template writes 2 copies.
