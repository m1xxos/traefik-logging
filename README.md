# traefik-logging

bench stand: two traefiks under synthetic load ship access logs through fluent-bit into one
log backend at a time, so the backends can be compared on cpu and ram. victorialogs, loki, elk
and openobserve, each as a single node and as a 3 node cluster.

* `terraform/` creates the vms on plusha (control-1, traefik-1, traefik-2, backend-1..3), same
  infisical creds and yandex state bucket as homelab: copy `yc.auto.tfvars` and
  `proxmox.auto.tfvars` from `homelab/terraform/0-infra`
* `ansible/` installs docker and deploys `stacks/` with compose. the one password in the repo
  (`BENCH_PASSWORD`, minio/postgres/openobserve root) is a throwaway for lan-only vms that are
  recreated every run
* `loadgen/` is the rps page on the control vm, `bench/run.sh` drives it and collects a csv.
  traffic is a weighted mix from `loadgen/gen-targets.py`: four services by Host (api, shop,
  auth, static), a dead `legacy` backend for 502s, an unknown host for 404s, ~2.5% 5xx, ~6% 4xx,
  1% slow, 15% POST

```
task deps
task tfinit
task bench BACKEND=victorialogs MODE=single
task bench-run BACKEND=victorialogs MODE=single
task teardown
```

grafana `http://192.168.1.60:3000` (bench dashboard + `traefik logs (victorialogs)` grouped by ServiceName), rps page `http://192.168.1.60:8000`, backend ui in
`terraform output backend_ui`. results land in `docs/results/`, the summary with charts is `docs/RESULTS.md`
(`task charts` regenerates them, `docs/charts.html` is the interactive version);
`docs/COMPARISON.md` puts the numbers next to access control, features, maturity and adoption.
