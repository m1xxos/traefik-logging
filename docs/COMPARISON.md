# Log backends for traefik access logs: the comparison

_Last updated: 2026-09-26_

Four backends fed the same traefik access logs through fluent-bit on the same vms (see
`RESULTS.md` for the method and the raw numbers, `charts.html` for the pictures). This file
adds what the numbers do not say: what each product can do, who can be given access to
what, and how safe a bet each one is. Sources are linked; "OSS" means the free self-hosted
edition, "paid" the vendor's enterprise or cloud tier.

## Resources, measured

Per traefik rps; two traefiks, so lines/s is double. `cpu` is the average over the step,
`memory` the peak working set of the whole stack (grafana counted for loki, kibana for elk,
minio/nats/postgres for the clusters), `disk` what the backend vms' disks wrote. Storage is
bytes per stored line after a full run, wal and caches included.

| backend | mode | 500 rps: cpu / mem / disk | 2000 rps: cpu / mem / disk | storage per line | notes |
|---|---|---|---|---|---|
| victorialogs | single | 0.10 / 0.24 GiB / 0.2 MB/s | 0.35 / 0.36 GiB / 0.6 MB/s | 44 B | cheapest on every axis |
| victorialogs | cluster | 0.09 / 0.45 GiB / 0.6 MB/s | 0.30 / 0.65 GiB / 0.9 MB/s | 47 B | 3 storage nodes, 1 copy of the data |
| loki | single | 0.11 / 0.63 GiB / 1.5 MB/s | 0.54 / 0.89 GiB / 6.3 MB/s | 71 B | grafana is 0.32 GiB of the memory |
| loki | cluster | 0.20 / 1.18 GiB / 4.7 MB/s | not measured | n/a | 3 copies (rf=3) + minio; 1000 and 2000 rps steps hit a host stall |
| elk | single | 0.19 / 5.29 GiB / 2.1 MB/s | 0.37 / 5.46 GiB / 4.9 MB/s | 162 B | memory is the jvm heap, flat at any load; 2000 rps step disk-bound at ~1800 lines/s |
| elk | cluster | not run | not run | | 2 copies (1 replica) |
| openobserve | single | 0.07 / 0.83 GiB / 0.2 MB/s | 0.39 / 1.10 GiB / 0.9 MB/s | 75 B | parquet alone is 34 B/line, the rest is wal and cache |
| openobserve | cluster | 0.08 / 1.93 GiB / 0.3 MB/s | 0.40 / 2.43 GiB / 1.5 MB/s | 148 B | 1 copy in minio; nats + postgres + minio on one node |

What the table says in one line each: victorialogs costs the least and writes the least;
openobserve is close on cpu and disk but holds 2-3x the memory; loki is fine single but its
cluster triples the writes (rf=3 + wal + object store), which is what made it the first to
fall over on this host; elk holds a fixed 5+ GiB for the jvm and kibana before the first
line arrives and indexes everything, so it is the heaviest on memory and disk.

## Access control: can one developer be given one service's logs?

The question that decides most rollouts. Short answer per product, details in each section
below.

| product | OSS: per-stream read access | how | paid tier |
|---|---|---|---|
| victorialogs | **yes, via vmauth** | oss vmauth user with `extra_stream_filters={service="foo"}` in its url prefix, filters are enforced server-side in subqueries too | enterprise adds mTLS and auto-TLS only, no rbac anywhere |
| loki | **no** | tenant is the only boundary; no auth at all in loki, no data source permissions in grafana oss | grafana enterprise + GEL or grafana cloud: label-based access control (LBAC) per team, GEL is end-of-life 2029 |
| elk | **yes, per data stream** | free basic tier: native user + role with `read` on one data stream; filtering by a field inside a stream is document-level security | platinum/enterprise: dls/fls, sso, ldap, audit |
| openobserve | **no** | oss roles exist but are not enforced, "all users have unrestricted access"; only an organisation per stream isolates | enterprise (free under 50 GB/day, call-home) or cloud: openfga rbac with per-stream permissions, needs ha mode |

## Grafana Loki

Sources checked 2026-09-26: [docs](https://grafana.com/docs/loki/latest/), [releases](https://github.com/grafana/loki/releases), Docker Hub API.

**Access control.** Loki has no authentication layer: "you must run an authenticating
reverse proxy in front of your services" ([authentication](https://grafana.com/docs/loki/latest/operations/authentication/)).
Isolation is by tenant only, the `X-Scope-OrgID` header that the proxy must set; loki checks
that the header is present, nothing else ([multi-tenancy](https://grafana.com/docs/loki/latest/operations/multi-tenancy/)).
A tenant cannot be limited to a label or a stream. Grafana OSS makes it worse: data source
permissions and RBAC are Enterprise/Cloud features, "any user can query all data sources"
([data source management](https://grafana.com/docs/grafana/latest/administration/data-source-management/)).
So with OSS the only way to give a developer their service and nothing else is one tenant
per service (the shipper sets the tenant header) plus one Grafana org or instance per group,
with the tenant header fixed on the data source. Label-based access control (a LogQL stream
selector such as `{service="foo"}` attached to a team) exists in Grafana Cloud and in
self-managed Grafana Enterprise with Grafana Enterprise Logs
([team LBAC](https://grafana.com/docs/grafana/latest/administration/data-source-management/teamlbac/),
[GEL LBAC](https://grafana.com/docs/enterprise-logs/latest/setup/lbac/)); it filters only the
stream selector, not `| label=` filters, and is not enforced for the ruler. GEL itself is in
LTS with no new features and end-of-life on 2029-02-01
([GEL docs](https://grafana.com/docs/enterprise-logs/latest/)), which points self-managed LBAC
users at Grafana Cloud. Pricing for Enterprise and GEL is not published; Cloud is free up to
50 GB/month, then $0.40/GB written ([pricing](https://grafana.com/pricing/)).

**Functionality.** LogQL with json/logfmt/pattern parsers and metric queries; structured
metadata for high-cardinality fields (schema v13, tsdb); pattern ingester and bloom filters
are experimental with no SLA; Logs Drilldown app ships with Grafana 12+; ruler for alerting
and recording rules; retention via the compactor, global, per tenant and per stream
(`retention_stream`), off by default ([retention](https://grafana.com/docs/loki/latest/operations/storage/retention/));
native OTLP ingestion since 3.0; Promtail is end-of-life since 2026-03-02, Alloy replaces it
([promtail](https://grafana.com/docs/loki/latest/send-data/promtail/)). Storage is tsdb index +
chunks in object storage, filesystem is not for production; replication factor 3 with a
write quorum of 2, so one ingester can be lost, two mean data loss; the WAL protects the
in-memory part ([components](https://grafana.com/docs/loki/latest/get-started/components/)).
Simple scalable mode is deprecated and removed in 4.0, which is a near rewrite (columnar
"DataObject" storage, Kafka as a second hard dependency, new query engine)
([ssd removal](https://grafana.com/whats-next/2026-08-24-loki-ssd-deployment-no-longer-available/),
[GrafanaCON 2026](https://grafana.com/blog/grafanacon-2026-announcements/)). No official
backup procedure: the state is the bucket.

**Reliability and maturity.** GA since 2019-11 (v1.0), 3.0 in 2024-04, current 3.7.8
(2026-09-17) with 3.6.x and 3.7.x both receiving patches; 25 releases in 2026 so far; minor
per quarter, patch once or twice a month, no formal LTS for OSS
([releases](https://github.com/grafana/loki/releases), [cadence](https://grafana.com/docs/loki/latest/release-notes/cadence/)).
Defaults bite: 4 MB/s ingestion, 3 MB/s per stream, 5000 streams per tenant, 5000 entries per
query ([configure](https://grafana.com/docs/loki/latest/configure/)). License AGPL-3.0 since
2021, clients and protobufs Apache-2.0 ([LICENSING.md](https://github.com/grafana/loki/blob/main/LICENSING.md)).

**Adoption.** 28,951 GitHub stars, 4,118 forks, 448 contributors, 4.8 billion Docker pulls
(2026-09-26). Adopters file lists Dropbox (4-5 PB, 1000+ services), Red Hat (OpenShift
Logging runs the Loki Operator), ASML, EverQuote
([ADOPTERS.md](https://github.com/grafana/loki/blob/main/ADOPTERS.md),
[Dropbox talk](https://grafana.com/events/grafanacon/2025/loki-at-dropbox-logging-at-petabyte-scale/)).
Grafana Labs: 7,000+ paying organisations, $400M ARR
([press, 2026-02](https://grafana.com/about/press/2026/02/03/grafana-labs-caps-a-breakout-year-of-growth-and-product-innovation/)).

**Risks.** Everything about access control is paid or cloud. The Helm chart moved out to
`grafana-community` in 2026-03 and the in-repo chart is "maintained for GEL users only"
([issue 20705](https://github.com/grafana/loki/issues/20705)); Promtail is gone; 4.0 changes
the architecture under you. Operationally the most tunable and the most fragile of the
four: rate limits, cardinality, singleton compactor, WAL disk, and in our bench the cluster
mode's write amplification (rf=3 + wal + object store) was the first to hurt.

## OpenObserve

Sources checked 2026-09-26: [docs](https://openobserve.ai/docs/), [releases](https://github.com/openobserve/openobserve/releases), GitHub API.

**Access control.** OSS has users, organisations, service accounts and a role enum
(Root/Admin/Editor/Viewer/User), but the roles are not enforced: "Open-source version: RBAC
is not supported. All users have unrestricted access to all features"
([users](https://openobserve.ai/docs/user-guide/users/)). The only isolation in OSS is the
organisation: put a stream in its own org and invite only the people who may see it. Custom
roles with per-stream permissions (the role editor stores permissions against individual
stream names) exist in Enterprise and Cloud, via an external OpenFGA
([RBAC](https://openobserve.ai/docs/user-guide/account-administration/identity-and-access-management/role-based-access-control/),
[enable RBAC](https://openobserve.ai/docs/user-guide/account-administration/identity-and-access-management/enable-rbac-in-openobserve-enterprise/)),
and only in HA mode: object storage + PostgreSQL + NATS + OpenFGA, no single-node path. SSO
(OIDC, LDAP, SAML via Dex) is Enterprise/Cloud too
([SSO](https://openobserve.ai/docs/user-guide/identity-and-access-management/sso/)).
Enterprise is a separate binary, free up to 50 GB/day without a key, sends usage data home
([enterprise license](https://openobserve.ai/enterprise-license/)); above the limit search is
blocked after three overages a month ([license and pricing](https://openobserve.ai/docs/enterprise-setup/license-and-pricing/)).
Ingestion tokens are org-scoped and ingest-only, service accounts in OSS have full access
([service accounts](https://openobserve.ai/docs/user-guide/account-administration/identity-and-access-management/service-accounts/)).

**Functionality.** SQL and PromQL, VRL pipelines, dashboards, scheduled and real-time
alerts, logs, metrics, traces and RUM in one binary; ingestion via `_json`/`_bulk`
(Elasticsearch compatible), OTLP, syslog, Prometheus remote write
([ingestion](https://openobserve.ai/docs/ingestion/)). Storage is parquet on local disk or
S3 with a Tantivy inverted index next to each file; retention per stream or global
(`ZO_COMPACT_DATA_RETENTION_DAYS`, default 3650) ([stream details](https://openobserve.ai/docs/user-guide/data-processing/streams/stream-details/)).
HA needs object storage, PostgreSQL for metadata and NATS for coordination (MySQL was dropped
in 0.70), roles router/ingester/querier/compactor/scheduler
([architecture](https://openobserve.ai/docs/architecture/)). An ingester that restarts loses
nothing; a dead disk loses up to `ZO_MAX_FILE_RETENTION_TIME` (10 minutes) of unflushed data
([vendor blog](https://openobserve.ai/blog/scaling-observability-peak-traffic/)). No backup
doc: the metadata store is PostgreSQL, and `recover-file-list` rebuilds it from the parquet
in object storage ([cli](https://openobserve.ai/docs/administration/maintenance/operator-guide/cli-commands/)).
Enterprise-only: RBAC, SSO, audit trail, redaction, federated search, downsampling,
incidents, AI assistant ([enterprise features](https://openobserve.ai/docs/enterprise-setup/enterprise-features/)).

**Reliability and maturity.** Repo from 2023-02; 1.0.0 GA on 2026-09-11 after 3.5 years of
0.x, then 1.0.1 to 1.0.4 within 13 days; seven 0.x minors in 2026 before that
([releases](https://github.com/openobserve/openobserve/releases)). The road to 1.0 had
breaking changes: WAL format changed in 0.92, MySQL removed in 0.70, non-downgradeable
migrations with mandatory intermediate versions in the 0.1x line, the usage stream moved to
Enterprise in 1.0. Open reports worth reading before trusting it with data: silent
ingestion loss under load on 0.91/0.92, attributed to WAL replay after an ingester restart
([issue 13869](https://github.com/openobserve/openobserve/issues/13869)), OTLP gRPC failures
reported as OK, VRL panics on the query thread; 582 open issues. Telemetry on by default
(`ZO_TELEMETRY`). License AGPL-3.0 for OSS, commercial for Enterprise.

**Adoption.** 22,142 stars, 1,112 forks, 156 contributors (2026-09-26); 759k Docker Hub
pulls (official images are on AWS ECR, so undercounted). OpenObserve Inc. raised a $10M
Series A in 2026-04 from Nexus and Dell Technologies Capital, claims 6,000+ organisations
([press](https://www.businesswire.com/news/home/20260429840147/en/OpenObserve-Raises-$10-Million-Series-A-to-Accelerate-AI-native-Observability));
Slack 1,800+ members, 3,600 active deployments (2025-04); case studies are cost stories
against Datadog ([customer stories](https://openobserve.ai/customer-stories/)).

**Risks.** Two weeks into 1.0, single VC-backed vendor, every access-control feature is
Enterprise, call-home in both editions, format churn through the 0.x line, and recent
data-loss reports. It was the best of the four in our bench on cpu and disk with a
fraction of ELK's memory; the risk is entirely in maturity and licensing, not performance.

## VictoriaLogs

Sources checked 2026-09-26: [docs](https://docs.victoriametrics.com/victorialogs/), [releases](https://github.com/VictoriaMetrics/VictoriaLogs/releases), GitHub API.

**Access control.** VictoriaLogs itself has one optional Basic-Auth credential for the whole
instance and per-endpoint auth keys, no users, no roles in any edition: "all the
VictoriaLogs components must run inside a protected trusted network", use vmauth in front
([security and lb](https://docs.victoriametrics.com/victorialogs/security-and-lb/)). What
makes it workable is that the restriction primitive is server-side and OSS: the query args
`extra_filters`, `extra_stream_filters` and `hidden_fields_filters` are "global constraints,
unconditionally propagated into all the subqueries", documented as the mechanism "for
reliable access control" ([querying](https://docs.victoriametrics.com/victorialogs/querying/)).
vmauth (OSS: basic auth, bearer, JWT, OIDC login; Enterprise: mTLS routing and IP filters)
maps a user to a `url_prefix` that carries the filter, and a client cannot override query
args that the prefix already sets ([vmauth](https://docs.victoriametrics.com/victoriametrics/vmauth/)).
The vendor's own example is exactly the question asked:
`url_prefix: "http://victoria-logs:9428/?extra_stream_filters={service=\"frontend-logs\"}"`
for a read-only user limited to `/select/.*`, optionally with `AccountID`/`ProjectID`
headers for tenant scoping and `hidden_fields_filters` to mask fields. JWT tokens can carry
the filters (`logs_extra_stream_filters` in the `vm_access` claim), so an IdP can hand them
out. Tenants are `(AccountID, ProjectID)` headers with no per-tenant authorisation of their
own; cross-tenant queries and per-tenant quotas are open issues earmarked Enterprise
([multitenancy](https://docs.victoriametrics.com/victorialogs/#multitenancy),
[issue 91](https://github.com/VictoriaMetrics/VictoriaLogs/issues/91),
[roadmap](https://docs.victoriametrics.com/victorialogs/roadmap/)). Enterprise for logs adds
mTLS between components and automatic TLS certificates, not RBAC
([enterprise flags](https://github.com/VictoriaMetrics/VictoriaLogs/blob/master/docs/victorialogs/victoria_logs_enterprise_flags.md)).
Caveats: an open bug where the filters are not applied on `/internal/` paths in multilevel
clusters ([issue 1260](https://github.com/VictoriaMetrics/VictoriaLogs/issues/1260)), and the
Grafana plugin has tenant headers per datasource but no datasource-wide default filter, so
enforcement belongs in vmauth, not Grafana ([grafana plugin](https://docs.victoriametrics.com/victorialogs/integrations/grafana/)).

**Functionality.** LogsQL with `stats by`, `top`, `facets`, `join`, `union`, `extract`,
`unpack_json`, `stream_context`, subqueries via `in()` ([logsql](https://docs.victoriametrics.com/victorialogs/logsql/));
vmui built in with live tailing and CSV export; Grafana datasource plugin v0.32.0 (8.5M
downloads) with logs, time series, table and alerting panels; alerting and recording rules
through vmalert (`type: vlogs`) ([vmalert](https://docs.victoriametrics.com/victorialogs/vmalert/)).
Ingestion: jsonline, Elasticsearch bulk, Loki push, OTLP, syslog, journald, Datadog, Splunk
HEC, so every shipper works unchanged ([data ingestion](https://docs.victoriametrics.com/victorialogs/data-ingestion/)).
Retention is global only (`-retentionPeriod`, default 7d) plus disk-usage caps; per-tenant
and per-stream retention are open requests ([issue 226](https://github.com/VictoriaMetrics/VictoriaLogs/issues/226)).
Cluster = vlinsert + vlselect + vlstorage, sharded with no replication: a lost vlstorage disk
loses that shard, a vlstorage outage makes queries return 502 unless partial responses are
allowed; HA means vlagent writing to two independent clusters
([cluster](https://docs.victoriametrics.com/victorialogs/cluster/), [vlagent](https://docs.victoriametrics.com/victorialogs/vlagent/)).
Backups are manual snapshots plus rsync, no object storage backend yet (open PR), no
downsampling, tiering by moving day partitions between instances
([backup and restore](https://docs.victoriametrics.com/victorialogs/#backup-and-restore)).

**Reliability and maturity.** 0.1 in 2023-06, 1.0 in 2024-11 with the vendor's "ready for
production use starting from v1.0.0" ([faq](https://docs.victoriametrics.com/victorialogs/faq/));
own repo since 2025-07. Latest 1.52.0 (2026-07-16) and a 1.51.1 compatibility patch
(2026-08-18); 10 releases in 2026 against 26 in 2025, nothing for six weeks
([releases](https://github.com/VictoriaMetrics/VictoriaLogs/releases)). Breaking changes
are frequent: `_time:d` semantics in 1.50, explicit `filter` pipes and a cluster protocol
bump in 1.51, an ordered upgrade path through 1.51.1 for 1.52
([changelog](https://docs.victoriametrics.com/victorialogs/changelog/)). Two auth holes
(Basic Auth skipped on reload endpoints, GET-based log deletion) are fixed only in the
unreleased tip ([issue 1635](https://github.com/VictoriaMetrics/VictoriaLogs/issues/1635)).
License Apache-2.0, no LTS line for logs.

**Adoption.** 2,317 stars on the young standalone repo (the monorepo it came from has
17,771), 364 contributors, 4.0M Docker Hub pulls, 8.5M Grafana plugin downloads
(2026-09-26). VictoriaLogs GA in VictoriaMetrics Cloud since 2026-02. Public users:
TrueFoundry made it the default for high-volume clusters after a 500 GB benchmark against
Loki ([truefoundry](https://www.truefoundry.com/blog/victorialogs-vs-loki)), Immich's
observability runs a 3-node cluster; the vendor's 32 case studies are all about metrics.
Telegram group ~700 members.

**Risks.** Bus factor: the founder authored 60% of all commits and, with one colleague,
62% of 2026's ([contributors](https://api.github.com/repos/VictoriaMetrics/VictoriaLogs/contributors)).
No replication in the cluster, security entirely on vmauth, per-stream retention missing,
release cadence slowed in 2026. For a homelab the positives outweigh: single binary,
7-day default retention, disk caps, and it was the cheapest of the four on every axis we
measured.

## Elasticsearch + Kibana

Sources checked 2026-09-26: [subscriptions](https://www.elastic.co/subscriptions) (tier columns
taken from the raw html and cross-checked against the license constants in the 9.5.4
source), [docs](https://www.elastic.co/docs/), [releases](https://github.com/elastic/elasticsearch/releases).

**Access control.** The only one of the four with real users, roles and index privileges
in the free tier: native/file realms, RBAC, API keys, TLS, Kibana Spaces and feature
controls are all in the Basic column, and security is auto-configured on first start
([subscriptions](https://www.elastic.co/subscriptions), [self setup](https://www.elastic.co/docs/deploy-manage/security/self-setup)).
An index privilege on a data stream name covers its backing indices through rollover
([data stream privileges](https://www.elastic.co/docs/deploy-manage/users-roles/cluster-or-deployment-auth/granting-privileges-for-data-streams-aliases)).
So the free recipe for "developer sees only their service" is: one data stream per service
(the `reroute` ingest processor splits by `service.name` into `logs-<dataset>-<namespace>`),
a role with `read` + `view_index_metadata` on that stream, Kibana `read` on Discover and
Dashboards in one Space, a native user with that role. Filtering *inside* one data stream
by a field value (`ServiceName: api`) is document-level security, which is Platinum and
above: `DOCUMENT_LEVEL_SECURITY_FEATURE = ... License.OperationMode.PLATINUM`
([SecurityField.java](https://raw.githubusercontent.com/elastic/elasticsearch/v9.5.4/x-pack/plugin/core/src/main/java/org/elasticsearch/xpack/core/security/SecurityField.java),
[DLS/FLS](https://www.elastic.co/docs/deploy-manage/users-roles/cluster-or-deployment-auth/controlling-access-at-document-field-level)).
Also paid: SSO (SAML, OIDC, JWT, Kerberos: Platinum), LDAP/AD, audit logging and IP
filtering (Gold), Kibana sub-feature privileges. Gold is discontinued and self-managed
Platinum is "existing customers only", so a new self-managed buyer's only paid tier is
Enterprise ([subscriptions pdf, 2026-07](https://www.elastic.co/pdf/subscriptions-2026-07-01.pdf)).

**Functionality.** Free: data streams, ILM and data stream lifecycle, downsampling,
snapshot/restore with SLM, ES|QL, Discover, Lens, dashboards, CSV export, cross-cluster
search, Elastic Agent and the OTLP endpoints (metrics GA since 9.2, logs and traces preview
in 9.5) ([otlp endpoint](https://www.elastic.co/docs/manage-data/ingest/otlp-endpoint)).
Alerting rules run on Basic but the only free connectors are "server log" and "write to an
index"; Slack, email, webhook, PagerDuty need Gold+ (`minimumLicenseRequired: 'gold'` in the
[connector source](https://raw.githubusercontent.com/elastic/kibana/v9.5.4/x-pack/platform/plugins/shared/stack_connectors/server/connector_types/slack/index.ts)).
Paid: ML anomaly detection (Platinum), Watcher and PDF reports (Gold), searchable
snapshots and cross-cluster replication (Enterprise). Replication is primary/replica shards
with automatic promotion when a node dies; one node "is not resilient", two need a
tiebreaker, three is the smallest production cluster
([small clusters](https://www.elastic.co/docs/deploy-manage/production-guidance/availability-and-resilience/resilience-in-small-clusters)).
Disk watermarks make indices read-only at 95%. Memory: heap pinned at Xms=Xmx and at most
50% of RAM, the rest is page cache, which is why our ELK vm sat at 5.3 GiB whatever the
load ([jvm settings](https://www.elastic.co/docs/reference/elasticsearch/jvm-settings)).

**Reliability and maturity.** Sixteen years old (2010-02); current 9.5.4 (2026-09-15) with
9.4.x and 8.19.x still patched, minors roughly quarterly (9.0 2025-04, 9.5 2026-08)
([releases](https://github.com/elastic/elasticsearch/releases)). Breaking changes are
documented per minor and majors require going through the last 8.x
([breaking changes](https://www.elastic.co/docs/release-notes/elasticsearch/breaking-changes)).
License: the source is triple-licensed AGPL-3.0 / SSPL / ELv2 since 8.16, but everything in
`x-pack` (all security, ILM, ML) is ELv2 only, and the shipped binaries are ELv2: fine to
self-host and embed, not to offer as a managed service
([LICENSE.txt](https://github.com/elastic/elasticsearch/blob/main/LICENSE.txt),
[licensing faq](https://www.elastic.co/pricing/faq/licensing)). OpenSearch is the Apache-2.0
fork of 7.10 under the Linux Foundation since 2024.

**Adoption.** 77,998 stars and 2,551 contributors on elasticsearch, 21,302 on kibana; 980M
Docker Hub pulls of the library image; #1 on DB-Engines search engines with 95.5 points,
but down 22.75 year over year while OpenSearch (#4) rises
([db-engines](https://db-engines.com/en/ranking/search+engine)); 28k+ companies per 6sense;
Siemens, Tinder, Docusign, PepsiCo on the customer page. Largest ecosystem and hiring pool
of the four by an order of magnitude.

**Risks.** The memory floor (5+ GiB before the first log line), the disk footprint (162
B/line, 3.7x victorialogs), operational weight (3 nodes for HA, watermarks, shard sizing,
upgrade paths), and the way security features end at Basic: filtering inside a stream, SSO,
audit and even a Slack alert connector are paid, and the only paid tier left for new
self-managed installs is Enterprise. Everything that is free is solid and battle-tested.

## What to pick

| need | pick | why |
|---|---|---|
| cheapest possible on cpu, memory and disk | victorialogs single | 0.35 cores / 0.36 GiB / 44 B per line at 4000 lines/s; single binary |
| per-service read access for free, no proxy games | elk (basic) | native users and roles, one data stream per service; costs 5 GiB and 4x the disk |
| per-service read access for free with a proxy | victorialogs + vmauth | vendor-documented `extra_stream_filters` per user; one shared credential inside |
| grafana is already the ui and logs must live next to metrics | loki single | fine at this scale; accept no per-stream rights in oss and a heavier cluster |
| one product for logs, metrics and traces with its own ui | openobserve | close to victorialogs on cost; two weeks into 1.0, rbac and sso are enterprise |
| per-stream rights and sso as a product feature, paid | elk enterprise, grafana cloud, openobserve enterprise | dls/fls, lbac, openfga respectively |

Cluster modes on this stand: victorialogs and openobserve shard without replicating (one
copy, a lost node is lost data or 502s), loki replicates three times and paid for it in
disk writes, elk keeps two copies and was not run. If durability of the log store matters
more than cost, loki cluster or elk cluster are the honest options; if the logs are
disposable after a week, victorialogs single is hard to argue with.
