#!/usr/bin/env bash
set -euo pipefail

# Rebuild the full Pinaka pipeline: init → ingest (raw) → bronze → gold
# All data is stored in MiniStack (ephemeral S3), so this restores it after a restart.
#
# Usage:
#   ./scripts/rebuild.sh
#   START_DATE=2026-05-18 END_DATE=2026-05-22 ./scripts/rebuild.sh
#   DATASET=bhavcopy_eq ./scripts/rebuild.sh        # single dataset
#   N=4 ./scripts/rebuild.sh                        # parallel workers

START_DATE="${START_DATE:-2026-05-18}"
END_DATE="${END_DATE:-2026-05-22}"
DATASET="${DATASET:-}"
MAX_WORKERS="${N:-4}"
SKIP_INIT="${SKIP_INIT:-}"

DOCKER_COMPOSE="COMPOSE_PROJECT_NAME=pinaka docker compose -f infra/docker/docker-compose.yml --env-file infra/docker/.env"

run_ingestion_image() {
  docker build -q -t pinaka-ingestion-worker -f services/ingestion-worker/Dockerfile . >/dev/null
}

run_ingest() {
  local ds="$1"
  echo "==> Ingesting raw data: $ds ($START_DATE -> $END_DATE)"
  DATASET="$ds" START_DATE="$START_DATE" END_DATE="$END_DATE" MAX_WORKERS="$MAX_WORKERS" \
    make ingest-range 2>&1 | tail -5
}

run_bronze() {
  local ds="$1"
  echo "==> Normalizing to bronze: $ds ($START_DATE -> $END_DATE)"
  DATASET="$ds" START_DATE="$START_DATE" END_DATE="$END_DATE" MAX_WORKERS="$MAX_WORKERS" \
    make bronze-range 2>&1 | tail -5
}

run_gold() {
  local ds="$1"
  echo "==> Computing gold features: $ds ($START_DATE -> $END_DATE)"
  DATASET="$ds" START_DATE="$START_DATE" END_DATE="$END_DATE" MAX_WORKERS="$MAX_WORKERS" \
    make gold-range 2>&1 | tail -5
}

echo "=== Pinaka Pipeline Rebuild ==="
echo "  Date range : $START_DATE -> $END_DATE"
echo "  Workers    : $MAX_WORKERS"
echo "  Dataset    : ${DATASET:-all}"
echo ""

# Step 0: Init infrastructure
if [ -z "$SKIP_INIT" ]; then
  echo "==> Initializing MiniStack resources (buckets + queues)"
  bash scripts/create_ministack_resources.sh
  echo ""
fi

# Step 1: Build ingestion image
run_ingestion_image

ALL_DATASETS=("bhavcopy_eq" "corp_actions" "index_constituents" "fo_oi" "block_deals")
GOLD_DATASETS=("bhavcopy_eq" "fo_oi")

if [ -n "$DATASET" ]; then
  # Single dataset mode
  run_ingest "$DATASET"
  run_bronze "$DATASET"
  if [[ " ${GOLD_DATASETS[*]} " == *" $DATASET "* ]]; then
    run_gold "$DATASET"
  fi
else
  # All datasets
  for ds in "${ALL_DATASETS[@]}"; do
    run_ingest "$ds"
  done

  for ds in "${ALL_DATASETS[@]}"; do
    run_bronze "$ds"
  done

  for ds in "${GOLD_DATASETS[@]}"; do
    run_gold "$ds"
  fi
fi

echo ""
echo "=== Rebuild complete ==="
echo "Run 'make health' to verify services."
echo "Run row count check:"
echo "  docker exec pinaka_dagster python -c \"import sys; sys.path.insert(0, '/opt/dagster/ingestion-src'); from pinaka_ingestion.pipeline.duckdb_layer import get_connection; con = get_connection(); [print(f'{v[0]}: {con.execute(f\\\"SELECT count(*) FROM {v[0]}\\\").fetchone()[0]} rows') for v in con.execute(\\\"SELECT table_name FROM information_schema.views WHERE table_schema='main' AND table_name LIKE 'bronze_%'\\\").fetchall()]\""
