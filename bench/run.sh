#!/usr/bin/env bash
# run.sh — Drive one benchmark round: step the RPS on both traefiks, wait, and
# pull avg CPU / max memory per backend container from vmsingle into a CSV.
# Usage: ./bench/run.sh <backend> <mode>  |  task bench-run BACKEND=loki MODE=cluster
# Env:   STEPS="100 500 1000 2000" STEP_MINUTES=15 WARMUP_MINUTES=5 DRAIN_MINUTES=10

set -euo pipefail

BACKEND="${1:?backend (victorialogs|loki|elk|openobserve)}"
MODE="${2:?mode (single|cluster)}"
CONTROL="${CONTROL:-192.168.1.60}"
LOADGEN="http://${CONTROL}:8000"
VM="http://${CONTROL}:8428"
STEPS="${STEPS:-100 500 1000 2000}"
STEP_MINUTES="${STEP_MINUTES:-15}"
WARMUP_MINUTES="${WARMUP_MINUTES:-5}"
DRAIN_MINUTES="${DRAIN_MINUTES:-10}"
# first two minutes of every step are settling time, not measured
SKIP_MINUTES=2
OUT="${OUT:-docs/results/${BACKEND}-${MODE}-$(date +%Y%m%d-%H%M).csv}"
BACKEND_RE='victorialogs|vlstorage|vlinsert|vlselect|loki|minio|elasticsearch|kibana|openobserve|nats|postgres'

set_rate() {
  local rate="$1"
  for t in traefik-1 traefik-2; do
    curl -fsS -o /dev/null -X POST "${LOADGEN}/set" -d "target=${t}&rate=${rate}"
  done
}

query() {
  # query <promql> -> prints value(s), one per line: "<label> <value>"
  curl -fsS "${VM}/api/v1/query" --data-urlencode "query=$1" \
    | python3 -c '
import sys, json
for r in json.load(sys.stdin)["data"]["result"]:
    name = r["metric"].get("name") or r["metric"].get("instance") or "total"
    print(name, r["value"][1])'
}

record() {
  local step="$1" window="$2"
  echo "==> Recording step ${step} rps over the last ${window}"
  query "avg_over_time((sum by (name) (rate(container_cpu_usage_seconds_total{name=~\"${BACKEND_RE}\"}[1m])))[${window}:1m])" \
    | while read -r name v; do echo "${BACKEND},${MODE},${step},${name},cpu_cores_avg,${v}"; done >> "${OUT}"
  query "max_over_time(container_memory_working_set_bytes{name=~\"${BACKEND_RE}\"}[${window}])" \
    | while read -r name v; do echo "${BACKEND},${MODE},${step},${name},mem_ws_max_bytes,${v}"; done >> "${OUT}"
  query "max_over_time(container_memory_rss{name=~\"${BACKEND_RE}\"}[${window}])" \
    | while read -r name v; do echo "${BACKEND},${MODE},${step},${name},mem_rss_max_bytes,${v}"; done >> "${OUT}"
  query "avg_over_time((sum(rate(container_cpu_usage_seconds_total{name=~\"${BACKEND_RE}\"}[1m])))[${window}:1m])" \
    | while read -r name v; do echo "${BACKEND},${MODE},${step},backend,cpu_cores_avg,${v}"; done >> "${OUT}"
  query "max_over_time((sum(container_memory_working_set_bytes{name=~\"${BACKEND_RE}\"}))[${window}:10s])" \
    | while read -r name v; do echo "${BACKEND},${MODE},${step},backend,mem_ws_max_bytes,${v}"; done >> "${OUT}"
  query "avg_over_time((sum(rate(traefik_entrypoint_requests_total{entrypoint=\"web\"}[1m])))[${window}:1m])" \
    | while read -r name v; do echo "${BACKEND},${MODE},${step},traefik,rps_achieved,${v}"; done >> "${OUT}"
  query "sum(increase(fluentbit_input_records_total[${window}]))" \
    | while read -r name v; do echo "${BACKEND},${MODE},${step},fluent-bit,records_in,${v}"; done >> "${OUT}"
  query "sum(increase(fluentbit_output_proc_records_total[${window}]))" \
    | while read -r name v; do echo "${BACKEND},${MODE},${step},fluent-bit,records_out,${v}"; done >> "${OUT}"
  query "sum(increase(fluentbit_output_retries_total[${window}]))" \
    | while read -r name v; do echo "${BACKEND},${MODE},${step},fluent-bit,retries,${v}"; done >> "${OUT}"
  query "sum(increase(fluentbit_output_errors_total[${window}]))" \
    | while read -r name v; do echo "${BACKEND},${MODE},${step},fluent-bit,errors,${v}"; done >> "${OUT}"
  query "sum by (instance) (delta(node_filesystem_avail_bytes{mountpoint=\"/\",instance=~\"192.168.1.6[345]:.*\"}[${window}]))" \
    | while read -r name v; do echo "${BACKEND},${MODE},${step},${name},disk_delta_bytes,${v}"; done >> "${OUT}"
}

mkdir -p "$(dirname "${OUT}")"
echo "backend,mode,rps_per_traefik,component,metric,value" > "${OUT}"

echo "==> ${BACKEND}/${MODE}: warmup ${WARMUP_MINUTES}m at 100 rps"
set_rate 100
sleep "$((WARMUP_MINUTES * 60))"

for step in ${STEPS}; do
  echo "==> ${step} rps per traefik for ${STEP_MINUTES}m"
  set_rate "${step}"
  sleep "$((STEP_MINUTES * 60))"
  record "${step}" "$((STEP_MINUTES - SKIP_MINUTES))m"
done

echo "==> Drain ${DRAIN_MINUTES}m"
set_rate 0
sleep "$((DRAIN_MINUTES * 60))"
record 0 "${DRAIN_MINUTES}m"

echo "==> Done: ${OUT}"
