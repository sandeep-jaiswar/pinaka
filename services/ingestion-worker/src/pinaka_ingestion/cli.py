from __future__ import annotations

import argparse
import json
from datetime import date

from .jobs import backfill_plan, ingest_dataset_for_date, ingest_dataset_range
from .nse_client import RAW_DATASETS


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pinaka ingestion CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("backfill-plan", help="Create chunked backfill plan")
    plan.add_argument("--dataset", choices=RAW_DATASETS, default="bhavcopy_eq")
    plan.add_argument("--start-date", required=True)
    plan.add_argument("--end-date", required=True)
    plan.add_argument("--chunk-days", type=int, default=30)

    ingest = subparsers.add_parser("ingest", help="Ingest one date partition for a dataset")
    ingest.add_argument("--dataset", choices=RAW_DATASETS, default="bhavcopy_eq")
    ingest.add_argument("--trade-date", required=True, help="YYYY-MM-DD")
    ingest.add_argument("--bucket", default="pinaka-raw")
    ingest.add_argument("--endpoint-url", default="http://localhost:4566")
    ingest.add_argument("--region", default="ap-south-1")
    ingest.add_argument("--dry-run", action="store_true")
    ingest.add_argument("--allow-reingest", action="store_true")

    ingest_range = subparsers.add_parser(
        "ingest-range",
        help="Ingest a date range for a dataset",
    )
    ingest_range.add_argument("--dataset", choices=RAW_DATASETS, default="bhavcopy_eq")
    ingest_range.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    ingest_range.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    ingest_range.add_argument("--chunk-days", type=int, default=30)
    ingest_range.add_argument("--max-workers", type=int, default=None, help="Parallel threads (default: CPU-bound)")
    ingest_range.add_argument("--bucket", default="pinaka-raw")
    ingest_range.add_argument("--endpoint-url", default="http://localhost:4566")
    ingest_range.add_argument("--region", default="ap-south-1")
    ingest_range.add_argument("--dry-run", action="store_true")
    ingest_range.add_argument("--continue-on-error", action="store_true")
    ingest_range.add_argument("--allow-reingest", action="store_true")

    args = parser.parse_args()

    if args.command == "backfill-plan":
        plan_rows = backfill_plan(
            dataset=args.dataset,
            start_date=parse_date(args.start_date),
            end_date=parse_date(args.end_date),
            chunk_days=args.chunk_days,
        )
        print(json.dumps(plan_rows, indent=2))
        return

    if args.command == "ingest":
        result = ingest_dataset_for_date(
            dataset=args.dataset,
            trade_date=parse_date(args.trade_date),
            bucket=args.bucket,
            endpoint_url=args.endpoint_url,
            region_name=args.region,
            dry_run=args.dry_run,
            allow_reingest=args.allow_reingest,
        )
        print(json.dumps(result, indent=2))
        return

    if args.command == "ingest-range":
        result = ingest_dataset_range(
            dataset=args.dataset,
            start_date=parse_date(args.start_date),
            end_date=parse_date(args.end_date),
            chunk_days=args.chunk_days,
            max_workers=args.max_workers,
            bucket=args.bucket,
            endpoint_url=args.endpoint_url,
            region_name=args.region,
            dry_run=args.dry_run,
            continue_on_error=args.continue_on_error,
            allow_reingest=args.allow_reingest,
        )
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
