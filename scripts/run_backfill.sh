#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=services/ingestion-worker/src python3 -m pinaka_ingestion.cli backfill-plan \
  --dataset bhavcopy \
  --start-date 2016-01-01 \
  --end-date 2016-03-31 \
  --chunk-days 15
