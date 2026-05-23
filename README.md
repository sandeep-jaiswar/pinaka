# Pinaka — Stock Screening Platform for NSE

Pinaka is an open-source stock screening platform focused on **fundamental + technical analysis** for NSE-listed securities. It ingests publicly available market data via `nselib`, processes it through a multi-tier data pipeline (raw → bronze → gold), and provides precomputed screening features on top of DuckDB.

## Core principles
- Open-source first
- Cloud-portable architecture (local emulation first, AWS-native deployment later)
- Strong backfill/idempotency guarantees
- Data contracts and quality checks from day one

## Tech stack

| Layer | Technology | Status |
|---|---|---|
| **Language** | Python 3.11+ | ✅ |
| **Orchestration** | Dagster OSS (1.13.3) | ✅ Implemented |
| **Queue/Stream** | Redpanda (Kafka API, v24.1.15) | ✅ Infrastructure ready |
| **Raw Lake** | S3-compatible (MiniStack S3) | ✅ Implemented |
| **Transform** | Polars + DuckDB (in-worker) | ✅ Implemented |
| **Analytics/Serving** | DuckDB (S3-backed views) | ✅ Implemented |
| **Metadata/State** | PostgreSQL 16 | ✅ Implemented |
| **Local AWS Emulator** | MiniStack | ✅ Implemented |

## What's implemented

### Data ingestion pipeline
- **5 dataset extractors** using `nselib`:
  - `bhavcopy_eq` — daily equity bhavcopy (price-volume data)
  - `corp_actions` — corporate actions (splits, dividends, bonuses)
  - `index_constituents` — index membership (NIFTY 50, NIFTY NEXT 50, etc.)
  - `fo_oi` — futures & options open interest
  - `block_deals` — block/bulk deal data
- **Raw landing zone** (`s3://pinaka-raw`) — immutable JSON per `(dataset, trade_date, run_id)`
- **Bronze normalization** (`s3://pinaka-bronze`) — schema mapping, type coercion, Parquet output
- **Gold features** (`s3://pinaka-gold`) — precomputed technical indicators, stored as Parquet:
  - SMA-20, EMA-20, RSI-14, MACD, MACD Signal, MACD Histogram (equities)
  - Net Futures/Options/Total, Long/Short Ratio, Put/Call Ratio (derivatives)
- **DuckDB S3-backed views** — interactive SQL analytics over bronze data
- **Idempotent ingestion** — partition existence check prevents duplicates; `--allow-reingest` for replay

### CLI tool (`pinaka-ingestion`)
- `backfill-plan` — generates chunked date-range plans
- `ingest` — ingests a single trade-date partition
- `ingest-range` — parallel ingestion over a date range
- `--dataset` flag to select any supported dataset
- `--continue-on-error` for resilient batch runs

### Orchestration (Dagster)
- Daily partitioned assets for all 5 raw datasets
- Corresponding bronze assets dependent on raw assets
- Gold feature assets for bhavcopy and fo_oi
- DuckDB view refresh asset
- Run coordinator and workspace configuration

### Infrastructure
- Docker Compose stack: MiniStack (S3), PostgreSQL 16, Redpanda (Kafka), Dagster webserver + daemon
- Kubernetes manifests (Kustomize) for `kind` deployments
- S3 bucket + SQS queue provisioning script

## Monorepo layout

```
.
├── data-contracts/           # Schema contracts (WIP)
├── docs/
│   ├── adr/                  # Architecture Decision Records
│   ├── architecture/         # HLD, pipeline design, backfill, SLAs
│   └── runbooks/             # Operational runbooks
├── infra/
│   ├── docker/               # Docker Compose + .env.example
│   └── k8s/                  # Kustomize manifests (base + overlays)
├── packages/
│   └── python/pinaka-common/ # Shared utilities (skeleton)
├── scripts/                  # Infra bootstrap, backfill runner
└── services/
    ├── ingestion-worker/      # Core ingestion + bronze/gold pipeline
    ├── orchestrator-dagster/  # Dagster asset definitions
    └── api-screening/         # Screening API (placeholder)
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
- Postgres (host): `localhost:5433`

### Ingest data

Single partition (any dataset):

```bash
TRADE_DATE=2026-05-22 DATASET=bhavcopy_eq make ingest
```

Supported datasets: `bhavcopy_eq`, `corp_actions`, `index_constituents`, `fo_oi`, `block_deals`.

Batch ingestion for a date range:

```bash
START_DATE=2026-05-20 END_DATE=2026-05-22 CHUNK_DAYS=5 DATASET=bhavcopy_eq make ingest-range
```

Plan a backfill without running:

```bash
START_DATE=2026-05-01 END_DATE=2026-05-22 CHUNK_DAYS=5 DATASET=bhavcopy_eq make backfill-plan
```

## Quick start (Kubernetes)

```bash
kubectl apply -k infra/k8s/overlays/local-kind
```

## Pipeline stages

```
nselib → Raw (JSON, S3) → Bronze (Parquet, S3) → Gold (Parquet, S3)
                                              ↕
                                        DuckDB views (SQL analytics)
```

## Next milestones

1. ✅ ~~Implement concrete nselib extractors~~ — already done for 5 datasets
2. ✅ ~~Bronze normalization pipeline~~ — Parquet, typed schemas
3. ✅ ~~Gold feature computation~~ — Parquet, technical indicators + OI metrics
4. ✅ ~~Docker Compose local stack for all services~~
5. ⏳ Data quality gates (Great Expectations or Soda Core)
6. ⏳ Screening API and first strategy endpoints
7. ⏳ CI/CD pipeline setup

Detailed design is in `docs/architecture/`.
