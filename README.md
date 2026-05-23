# Pinaka Monorepo (Data Platform First)

Pinaka is a stock screening platform focused on **fundamental + technical analysis** for NSE-listed securities using `nselib` as the primary public data source.

This repository is structured as a monorepo so we can grow cleanly into:
- ingestion and transformation pipelines
- screening APIs
- alerting and strategy engines
- multiple UIs and internal tools

## Core principles
- Open-source first
- Cloud-portable architecture (local emulation first, AWS-native deployment later)
- Strong backfill/idempotency guarantees
- Data contracts and quality checks from day one

## Local cloud strategy
- Default local AWS emulator: **MiniStack** (`ministackorg/ministack`)
- Fallback option: LocalStack (if team preference or compatibility need)

## Proposed platform (phase 1)
- Orchestration: Dagster OSS
- Queue/stream: Redpanda (Kafka API)
- Raw lake: S3-compatible bucket (MiniStack S3)
- Warehouse/serving: ClickHouse + dbt-clickhouse
- Metadata/state: PostgreSQL

## Monorepo layout

```text
.
├── data-contracts/
├── docs/
│   ├── adr/
│   ├── architecture/
│   └── runbooks/
├── infra/
│   ├── docker/
│   └── k8s/
├── packages/
│   └── python/
├── scripts/
└── services/
    ├── ingestion-worker/
    ├── orchestrator-dagster/
    └── api-screening/
```

## Quick start (Docker)

```bash
cp infra/docker/.env.example infra/docker/.env
make up
make ministack-init
```

Then verify:

```bash
make health
```

Local endpoints:
- MiniStack: `http://localhost:4566`
- Dagster UI: `http://localhost:3000`
- Postgres (host): `localhost:5433` (container still uses `5432`)

Run first real ingestion (single partition):

```bash
TRADE_DATE=2026-05-22 make ingest-bhavcopy-eq
```

This target runs inside Docker and writes to MiniStack S3.
By default, ingestion is idempotent for a date partition and skips if that date already exists.
Use `--allow-reingest` from CLI only when you intentionally want a replay.

Run batch ingestion for a date range:

```bash
START_DATE=2026-05-20 END_DATE=2026-05-22 CHUNK_DAYS=5 make ingest-bhavcopy-eq-range
```

## Quick start (Kubernetes)

Use `kind` or `minikube`:

```bash
kubectl apply -k infra/k8s/overlays/local-kind
```

## Next milestones
1. Implement concrete `nselib` extractors per domain (`price`, `corporate actions`, `results`, `deliverables`, `derivatives`).
2. Add dbt models for bronze/silver/gold layers in ClickHouse.
3. Add data quality gates (Great Expectations or Soda Core).
4. Add screening API and first strategy endpoints.

Detailed design is in `docs/architecture/`.

- `overview.md` - platform boundaries and component map
- `data-pipeline-hld.md` - ingest to serving layer blueprint
- `backfill-mechanism.md` - replay and correction controls
- `datasets-and-slas.md` - dataset coverage and SLO targets
