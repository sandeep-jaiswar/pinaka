# Data Pipeline HLD (Ingestion First)

## 1. Pipeline layers

1. Extract (source pull)
- `nselib` clients fetch data by dataset and date partition.
- each pull writes immutable raw files to S3 path convention:
  `s3://pinaka-raw/nse/{dataset}/dt=YYYY-MM-DD/run_id=<uuid>/part-*.json`

2. Normalize (bronze)
- schema alignment, type coercion, source metadata enrichment.
- append-only, no business logic.

3. Validate (quality gates)
- mandatory column checks
- uniqueness checks for business keys
- freshness checks by dataset SLA
- failed partitions routed to quarantine bucket prefix.

4. Transform (silver)
- canonical security master joins
- corporate action adjustments (split/bonus/dividend awareness)
- dedupe and late-arrival reconciliation

5. Feature build (gold)
- technical indicators (EMA, RSI, MACD, ATR, VWAP variants)
- fundamental composites (quality, value, leverage, growth)
- screening-ready denormalized marts in ClickHouse

## 2. Partition strategy
- Primary partition: trading date (`trade_date`).
- Secondary logical partition: dataset (`bhavcopy`, `deliverable`, `fo_oi`, etc).
- Optional tertiary: symbol bucket for high-cardinality backfills.

## 3. Idempotency model
- ingestion key: `(dataset, partition_date, symbol?, source_hash)`
- write-once raw with run-scoped path
- upsert/merge in curated layers using deterministic business key
- watermark table tracks committed partition version

## 4. Orchestration model (Dagster)
- partitioned assets by daily partition definition
- schedule:
  - T+0 evening load for EOD datasets
  - retry windows for late availability
- sensors:
  - detect missing partitions
  - trigger dependent transforms after extract success

## 5. Backpressure and resiliency
- queue-based fanout for heavy symbol/date workloads
- bounded worker concurrency per dataset
- exponential backoff for source/API errors
- circuit-breaker when repeated source failures occur

## 6. Observability
- metrics: partition success rate, lag, row deltas, null rates, retry counts
- logs: structured JSON with `run_id`, `dataset`, `partition`
- lineage: asset-level DAG in Dagster + table-level docs via dbt

## 7. Data stores
- Raw + curated lake: MiniStack S3 bucket
- Serving tables: ClickHouse
- Metadata/state: Postgres
- Optional fast cache for API responses: Redis (later)
