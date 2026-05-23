# Backfill Mechanism Design

## 1. Why explicit backfill design matters
For stock analytics, historical consistency is as important as current freshness. A bad backfill can silently corrupt factor histories and invalidate strategy results.

## 2. Backfill job contract
A backfill request includes:
- `dataset`
- `start_date`
- `end_date`
- `mode` (`missing_only` | `recompute`)
- `chunk_days` (default 30)
- `max_parallel_chunks`
- `priority`

## 3. Execution flow
1. Planner creates chunked partition plan.
2. Validator excludes non-trading days (calendar-aware).
3. Executor launches chunk tasks.
4. Each task:
- extracts raw
- validates
- writes bronze/silver/gold (or selected stage)
- updates watermark + audit row
5. Reconciler runs row-count and checksum comparisons.
6. Promote only if checks pass.

## 4. Safety controls
- Dry-run mode to preview affected partitions.
- Canary mode: run first chunk and await manual/automatic gate.
- Hard cap on date span per run.
- Kill switch to pause all backfills.

## 5. Idempotency + replay
- Every chunk has deterministic `chunk_id`.
- Re-running chunk overwrites curated partition version while preserving raw immutable history.
- `recompute` mode invalidates downstream dependent partitions and re-materializes.

## 6. Audit and traceability
`ingestion_backfill_runs` table fields:
- `backfill_id`, `dataset`, `range_start`, `range_end`
- `status`, `chunks_total`, `chunks_done`, `chunks_failed`
- `requested_by`, `requested_at`, `completed_at`
- `code_version`, `config_hash`

## 7. Performance strategy
- chunk sizing by dataset weight
- symbol sharding for expensive partitions
- optional ephemeral compute burst on Kubernetes
- queue depth based worker autoscaling
