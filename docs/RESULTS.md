# Results

_Last updated: 2026-09-24_

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

| backend | mode | rps/traefik | rps achieved | backend cpu cores | backend mem max | disk write | disk busy max | retries | errors | disk growth | per container (cpu / mem) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| elk | single | 0 | 0 | 0.28 | 5.45 GiB | 4.3 MB/s | 17% | 0 | 0 | -1.19 GiB | elasticsearch 0.25 / 4.40 GiB, kibana 0.02 / 1.05 GiB |
| elk | single | 100 | 200 | 0.10 | 5.28 GiB | 0.7 MB/s | 11% | 0 | 0 | 0.02 GiB | elasticsearch 0.08 / 4.23 GiB, kibana 0.02 / 1.05 GiB |
| elk | single | 500 | 1000 | 0.19 | 5.29 GiB | 2.1 MB/s | 26% | 0 | 0 | 0.16 GiB | elasticsearch 0.17 / 4.24 GiB, kibana 0.02 / 1.05 GiB |
| elk | single | 1000 | 2000 | 0.27 | 5.34 GiB | 4.7 MB/s | 45% | 0 | 0 | 0.30 GiB | elasticsearch 0.31 / 4.29 GiB, kibana 0.01 / 1.05 GiB |
| elk | single | 2000 | 2951 | 0.37 | 5.46 GiB | 4.9 MB/s | 51% | 0 | 0 | 1.12 GiB | elasticsearch 0.36 / 4.41 GiB, kibana 0.01 / 1.05 GiB |
| loki | cluster | 100 | 200 | 0.08 | 0.75 GiB | 1.0 MB/s | 1% | 0 | 0 | -0.02 GiB | loki x3 0.07 / 0.16 GiB each, loki-grafana 0.01 / 0.22 GiB, minio 0.00 / 0.09 GiB |
| loki | cluster | 500 | 1000 | 0.20 | 1.18 GiB | 4.7 MB/s | 2% | 0 | 0 | 0.80 GiB | loki x3 0.18 / 0.29 GiB each, loki-grafana 0.01 / 0.22 GiB, minio 0.00 / 0.10 GiB |
| loki | cluster | 1000 | 1553 | 0.09 | 1.55 GiB | 1.4 MB/s | 60% | 0 | 0 | -0.27 GiB | loki x3 0.07 / 0.42 GiB each, loki-grafana 0.02 / 0.22 GiB, minio 0.00 / 0.10 GiB |
| loki | single | 0 | 286 | 0.07 | 0.84 GiB | 0.5 MB/s | 0% | 0 | 0 | -1.75 GiB | loki 0.06 / 0.53 GiB, loki-grafana 0.02 / 0.32 GiB |
| loki | single | 100 | 200 | 0.04 | 0.47 GiB | 0.3 MB/s | 0% | 0 | 0 | -0.01 GiB | loki 0.03 / 0.15 GiB, loki-grafana 0.01 / 0.32 GiB |
| loki | single | 500 | 1000 | 0.11 | 0.63 GiB | 1.5 MB/s | 1% | 0 | 0 | 0.26 GiB | loki 0.10 / 0.31 GiB, loki-grafana 0.01 / 0.32 GiB |
| loki | single | 1000 | 2000 | 0.21 | 0.77 GiB | 3.1 MB/s | 1% | 0 | 0 | 0.24 GiB | loki 0.20 / 0.45 GiB, loki-grafana 0.01 / 0.32 GiB |
| loki | single | 2000 | 4000 | 0.54 | 0.89 GiB | 6.3 MB/s | 2% | 0 | 0 | 0.52 GiB | loki 0.52 / 0.57 GiB, loki-grafana 0.01 / 0.32 GiB |
| openobserve | single | 100 | 200 | 0.02 | 0.58 GiB | 0.1 MB/s | 0% | 0 | 0 | 0.04 GiB | openobserve 0.02 / 0.58 GiB |
| openobserve | single | 500 | 1000 | 0.07 | 0.85 GiB | 0.6 MB/s | 1% | 0 | 0 | 0.04 GiB | openobserve 0.07 / 0.85 GiB |
| victorialogs | cluster | 0 | 386 | 0.04 | 0.58 GiB | 0.1 MB/s | 0% | 0 | 0 | 0.01 GiB | vlinsert 0.01 / 0.08 GiB, vlselect 0.00 / 0.01 GiB, vlstorage x3 0.03 / 0.18 GiB each |
| victorialogs | cluster | 100 | 200 | 0.04 | 0.37 GiB | 0.8 MB/s | 1% | 0 | 0 | 0.01 GiB | vlinsert 0.01 / 0.02 GiB, vlselect 0.00 / 0.03 GiB, vlstorage x3 0.03 / 0.12 GiB each |
| victorialogs | cluster | 500 | 1000 | 0.09 | 0.45 GiB | 0.6 MB/s | 1% | 0 | 0 | 0.03 GiB | vlinsert 0.02 / 0.04 GiB, vlselect 0.00 / 0.01 GiB, vlstorage x3 0.07 / 0.15 GiB each |
| victorialogs | cluster | 1000 | 2000 | 0.15 | 0.60 GiB | 0.7 MB/s | 1% | 0 | 0 | 0.07 GiB | vlinsert 0.04 / 0.08 GiB, vlselect 0.00 / 0.01 GiB, vlstorage x3 0.11 / 0.19 GiB each |
| victorialogs | cluster | 2000 | 4000 | 0.30 | 0.65 GiB | 0.9 MB/s | 1% | 0 | 0 | 0.14 GiB | vlinsert 0.10 / 0.11 GiB, vlselect 0.00 / 0.01 GiB, vlstorage x3 0.20 / 0.21 GiB each |
| victorialogs | single | 0 | 371 | 0.05 | 0.28 GiB | 0.1 MB/s | 2% | 0 | 0 | 0.01 GiB | victorialogs 0.05 / 0.28 GiB |
| victorialogs | single | 100 | 200 | 0.02 | 0.21 GiB | 0.1 MB/s | 1% | 0 | 0 | 0.01 GiB | victorialogs 0.02 / 0.21 GiB |
| victorialogs | single | 500 | 1000 | 0.10 | 0.24 GiB | 0.2 MB/s | 2% | 0 | 0 | 0.03 GiB | victorialogs 0.10 / 0.24 GiB |
| victorialogs | single | 1000 | 2000 | 0.18 | 0.27 GiB | 0.4 MB/s | 2% | 0 | 0 | 0.09 GiB | victorialogs 0.18 / 0.27 GiB |
| victorialogs | single | 2000 | 4000 | 0.35 | 0.36 GiB | 0.6 MB/s | 6% | 0 | 0 | 0.14 GiB | victorialogs 0.35 / 0.36 GiB |

`rps/traefik = 0` is the 10 minute drain after the last step: what the backend costs while it
digests its buffers and merges with no new input. `disk write` is what the backend vms' disks
see (node-exporter, sda, all backend vms summed); `disk busy max` is the busiest backend vm's
io time fraction. Disk io rows for the first four runs were backfilled from vmsingle (same
PromQL, evaluated at the original step windows), so they are as good as the live ones.

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

### loki cluster, 2026-09-22 (two attempts, valid up to 500 rps)

- First attempt: steps 100/500/1000 clean, then a host-wide i/o stall on plusha during the 2000
  rps step (20:50-21:05 local): minio took its drive offline after 30s without a completed
  write, the kernel reported hung tasks on backend-1 (minio, 122s) and on traefik-2
  (fluent-bit and jbd2, 245s and 368s), disk busy 37-62% on every vm including control-1.
  Only 3.81M of 6.55M lines made it into loki. Csv kept in `results/invalid/`.
- Second attempt, fresh vms and the fixes below: steps 100 and 500 clean (lines read = lines
  written, discarded 0, loki 0.18 cores / 0.29 GiB per node at 500 rps). The 1000 rps step
  stalled the host again (20:35-20:45 local: jbd2 blocked 245s on backend-1, loki blocked on
  backend-2/3, disk busy up to 82%, fluent-bit read 69k of 805k lines). The run was stopped
  by hand to keep the stall away from the main cluster on the same disk.
- The trigger is loki cluster's write amplification, not loki itself: three ingesters each
  writing wal + chunks, plus the chunk uploads into minio on the same physical disk, is ~10
  MB/s of writes at 1000 rps against 0.7 MB/s for the victorialogs cluster and 3.1 MB/s for
  loki single, neither of which ever stalled plusha. **On this host loki cluster cannot be
  measured above 500 rps per traefik.**
- Two real findings came out of the first attempt anyway:
  1. **fluent-bit + logrotate lose data when the backend is slow.** Push latency went to
     1.9s p99, fluent-bit paused the tail on backpressure, logrotate renamed the file, and
     after `Rotate_Wait 30` the unread tail was dropped: no error, no retry, no dropped-records
     metric, just 86% of the step gone. Now `Rotate_Wait 600` and logrotate `size 2G rotate 4`.
  2. **A grafana explore query can oom an ingester.** loki on backend-1 (limit 1536m) was
     oom-killed while serving `sum(count_over_time({...}[2s])) by (detected_level)` (the
     explore log-volume histogram). Now `querier.max_concurrent 2`, `max_query_parallelism 4`,
     and node 1 has 1792m for loki (grafana 448m, minio 512m). With nobody querying, the
     second attempt stayed at 0.29 GiB per node at 500 rps against 1.82 GiB the first time.

### elk single, 2026-09-23 (2000 rps step cut to 11 minutes)

- 5 532 788 access lines stored = lines read = lines shipped; no loss, retries 0. The total is
  below the usual 6.55M because the 2000 rps step was stopped by hand after 11 minutes.
- Memory is a flat ~5.3 GiB whatever the load: `-Xms3g -Xmx3g` is allocated up front (4.2 GiB
  rss with off-heap), kibana is another 1.05 GiB idle. That is the price of the jvm and the
  ui, not of the log volume; the victorialogs/loki numbers grow with load, elk's do not.
- CPU is modest (0.36 cores at the top step) because elasticsearch never got to use it: the
  step is disk-bound. At 2000 rps per traefik it indexed ~1800 lines/s of the 4000 offered,
  fluent-bit filled its 64-chunk buffer and paused the tail, elasticsearch logged
  `writing cluster state took [15694ms]`, `health check of [data] took [11406ms]` and one
  118s stall. The load was stopped early to keep plusha out of a host-wide stall (disk busy
  had reached 76% on backend-1 and 48% on the idle control-1); the buffer then drained
  completely at ~2400 lines/s, so nothing was lost.
- 897 MB on disk for 5.53M lines (~160 B/line): 3.7x victorialogs, 2.3x loki. Every string is
  keyword-indexed plus `_source`, so this is close to the raw size.
- **On this host elk single tops out around 1800 lines/s; the cluster mode (2 copies plus
  translog on three vms) would stall the disk the way loki cluster did.**

### openobserve single, 2026-09-24 (valid up to 500 rps, host stall at 1000)

- Steps 100 and 500 clean: lines read = lines written, retries 0. 0.02 cores / 0.58 GiB at 100
  rps, 0.07 cores / 0.85 GiB at 500; at 1000 rps it was running at 0.19 cores / 0.83 GiB and
  writing 0.4 MB/s when the host stalled. Fields are lowercased on ingest (`servicename`,
  `downstreamstatus`), grouping is plain SQL in its own ui.
- **The stall had nothing to do with the backend this time.** openobserve wrote 0.4 MB/s, yet
  vmsingle on control-1 hung (`victoria-metric blocked for more than 122 seconds`), fluent-bit
  and journald hung on traefik-1, vmsingle answered 429 after 10s. Same signature as the two
  loki-cluster stalls, at a fraction of the write load. The main cluster on plusha is powered
  off, so it is not longhorn rebuilding: the disk itself got slow. At the 1000 rps step
  traefik-1 wrote 8.9 MB/s on 21-22.09 with its disk 13-19% busy; on 23.09 it wrote 3.1 MB/s
  with the disk 33% busy and idle control-1 at 57%; on 24.09 the host stalled at ~1.5 MB/s.
  Same vms, same load, 3-6x less written, 2-4x busier: the change is on the host, after the
  power cycles of 22/23.09. Check there before any further run: `iostat -x 5`,
  `smartctl -a` / `nvme smart-log` on the pve-nvme device (wear, media errors, thermal
  throttling), host `dmesg` for nvme resets, thin pool metadata usage (`lvs -a`).
- Side finding: the go-httpbin/whoami containers behind traefik log every request to stdout
  and docker's json-file driver wrote 3.7 MB/s per traefik vm on top of the 1.9 MB/s access
  log (3.5 GB of json for `api` after two days). Now `logging: driver: none` for them.
- The run should be repeated for the 1000/2000 numbers once the host is stable.

## Disk

| run | disk write at 2000 rps | on disk after 6.55M lines |
|---|---|---|
| victorialogs single | 0.6 MB/s | 286 MB |
| victorialogs cluster | 0.9 MB/s (3 nodes) | 307 MB |
| loki single | 6.3 MB/s | 465 MB |
| loki cluster | 9.5 MB/s at 1000 rps (3 nodes + minio) | 548 MB in minio + ~40 MB wal/index per node |
| elk single | 4.9 MB/s (disk-bound, ~1800 lines/s indexed) | 897 MB after 5.53M lines |

Raw input is ~6.4 MB/s at 2000 rps. victorialogs writes less to disk than it receives (it
compresses in memory before flushing), loki writes about as much as it receives in single
mode and ~3x in cluster mode (replication_factor 3 plus wal on every node plus the chunk
upload to minio on the same disk).

## Things that bite

- **Memory limits are cgroup limits.** A backend that hits `mem_limit` gets OOM-killed and
  restarts; check `container_last_seen` gaps before trusting a low RSS number.
- Loki `per_stream_rate_limit` is raised to 32MB; with the default 3MB/s a single host+service
  stream is throttled at ~1000 rps and the numbers only show the throttle.
- ELK needs `vm.max_map_count=1048576` (ansible sets it), and the cluster template writes 2 copies.
- **plusha's disk stalls.** Host-wide i/o stalls on 2026-09-22 (twice, under loki cluster at
  ~10 MB/s), 2026-09-23 (elk single at 5 MB/s, load stopped early) and 2026-09-24 (openobserve
  single at 0.4 MB/s). The write load of the backend stopped explaining it on the third day;
  the host itself needs looking at. Check `disk busy max` and
  the kernel log (`dmesg | grep "blocked for more"`) before trusting a step, and rerun it.
- **After a host reboot run `task deploy`.** All vms come back (`on_boot`), but traefik did not
  on either traefik vm after plusha was powered off on 2026-09-22 (exit 137 during the docker
  shutdown, the other containers restarted fine). The bench then ran against nothing for 20
  minutes: fluent-bit healthy, elasticsearch healthy, zero lines.
- **Never trust "no errors" from fluent-bit alone.** Compare `fluentbit_input_records_total`
  with traefik's request counter: the rotation loss above showed 0 errors and 0 retries.
