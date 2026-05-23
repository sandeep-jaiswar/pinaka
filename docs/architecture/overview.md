# Pinaka Architecture Overview (HLD)

## 1. Product context
Pinaka is a full-stack stock intelligence company-in-a-repo targeting NSE market participants. Core capability is screening stocks using combined:
- fundamental signals (ratios, balance sheet derived fields, filings proxies)
- technical signals (trend, momentum, volatility, volume behavior)

## 2. Architecture goals
- Data freshness: daily EOD baseline, intraday extensibility.
- Correctness: deterministic, idempotent pipelines.
- Scalability: monorepo with independently deployable services.
- Cloud portability: local AWS emulation now, real AWS later with minimal rewiring.

## 3. System boundaries
### In scope now
- ingestion architecture
- backfill mechanism
- data quality and lineage foundations
- Docker + Kubernetes runtime baseline

### Out of scope now (but designed for)
- user auth/billing
- advanced recommendation models
- full UI surface

## 4. High-level components
1. Source connectors (`nselib` and future alt sources).
2. Orchestrator (Dagster) controlling scheduled loads + backfills.
3. Raw landing zone on S3 (`s3://pinaka-raw`).
4. Curated layers (`bronze/silver/gold`) on S3 and ClickHouse.
5. Event bus (Redpanda) for decoupled downstream tasks.
6. State and control plane in PostgreSQL (`ingestion_state`, `run_audit`, `watermarks`).
7. Screening API service reading Gold layer + feature tables.

## 5. AWS mapping (future)
- EKS: service runtime
- S3: data lake
- MSK or Kinesis: stream/event bus
- RDS Postgres: metadata/state
- ECR: images
- CloudWatch: logs/metrics
- IAM/Secrets Manager/KMS: security controls

## 6. Local equivalent mapping (today)
- MiniStack: S3/SQS/Secrets/IAM-compatible API endpoints
- Redpanda container: Kafka-compatible bus
- Postgres container: metadata DB
- Kind/minikube: local Kubernetes target

## 7. Why this monorepo strategy
- shared contracts and schemas avoid cross-repo drift
- infra and app changes version together
- enables atomic commits for pipeline + schema + deployment updates
