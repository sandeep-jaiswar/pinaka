from __future__ import annotations

import argparse
import json
from datetime import date

from .jobs import backfill_plan, ingest_bhavcopy_eq_for_date, ingest_bhavcopy_eq_range


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pinaka ingestion CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("backfill-plan", help="Create chunked backfill plan")
    plan.add_argument("--dataset", default="bhavcopy")
    plan.add_argument("--start-date", required=True)
    plan.add_argument("--end-date", required=True)
    plan.add_argument("--chunk-days", type=int, default=30)

    ingest_bhav = subparsers.add_parser("ingest-bhavcopy-eq", help="Fetch one bhavcopy EQ partition and write raw JSON")
    ingest_bhav.add_argument("--trade-date", required=True, help="YYYY-MM-DD")
    ingest_bhav.add_argument("--bucket", default="pinaka-raw")
    ingest_bhav.add_argument("--endpoint-url", default="http://localhost:4566")
    ingest_bhav.add_argument("--region", default="ap-south-1")
    ingest_bhav.add_argument("--dry-run", action="store_true")
    ingest_bhav.add_argument("--allow-reingest", action="store_true")

    ingest_bhav_range = subparsers.add_parser(
        "ingest-bhavcopy-eq-range",
        help="Fetch bhavcopy EQ for a date range and write one raw JSON per date",
    )
    ingest_bhav_range.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    ingest_bhav_range.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    ingest_bhav_range.add_argument("--chunk-days", type=int, default=30)
    ingest_bhav_range.add_argument("--bucket", default="pinaka-raw")
    ingest_bhav_range.add_argument("--endpoint-url", default="http://localhost:4566")
    ingest_bhav_range.add_argument("--region", default="ap-south-1")
    ingest_bhav_range.add_argument("--dry-run", action="store_true")
    ingest_bhav_range.add_argument("--continue-on-error", action="store_true")
    ingest_bhav_range.add_argument("--allow-reingest", action="store_true")

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

    if args.command == "ingest-bhavcopy-eq":
        result = ingest_bhavcopy_eq_for_date(
            trade_date=parse_date(args.trade_date),
            bucket=args.bucket,
            endpoint_url=args.endpoint_url,
            region_name=args.region,
            dry_run=args.dry_run,
            allow_reingest=args.allow_reingest,
        )
        print(json.dumps(result, indent=2))
        return

    if args.command == "ingest-bhavcopy-eq-range":
        result = ingest_bhavcopy_eq_range(
            start_date=parse_date(args.start_date),
            end_date=parse_date(args.end_date),
            chunk_days=args.chunk_days,
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
