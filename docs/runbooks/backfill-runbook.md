# Runbook: Backfill Operations

## Pre-checks
1. Confirm source availability for requested dates.
2. Confirm target buckets exist and are writable.
3. Confirm worker pool capacity.
4. Enable alerts for failure notifications.

## Standard run
```bash
PYTHONPATH=services/ingestion-worker/src python3 -m pinaka_ingestion.cli backfill-plan \
  --start-date 2018-01-01 \
  --end-date 2020-12-31 \
  --chunk-days 30
```

Then execute via orchestrator (preferred) or direct CLI runner.

## Validation checklist
- Missing partition count = 0 for target interval.
- Row deltas within expected tolerance.
- Quality checks pass for key tables.

## Rollback approach
- curated layer only: rollback partition versions
- raw layer: immutable, never deleted during rollback

## Escalation triggers
- >5% chunks failed
- checksum drift on critical tables
- repeated source parse errors across chunks
