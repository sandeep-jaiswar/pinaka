from __future__ import annotations

import argparse
import json
from datetime import date, timedelta

from .jobs import backfill_plan, ingest_dataset_for_date, ingest_dataset_range
from .nse_client import RAW_DATASETS
from .pipeline.gold import compute_features_for_date, compute_fo_oi_features_for_date

GOLD_DATASETS = ["bhavcopy_eq", "fo_oi"]


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

    gold = subparsers.add_parser("gold", help="Compute gold features for one date")
    gold.add_argument("--dataset", choices=GOLD_DATASETS, default="bhavcopy_eq")
    gold.add_argument("--trade-date", required=True, help="YYYY-MM-DD")
    gold.add_argument("--bronze-bucket", default="pinaka-bronze")
    gold.add_argument("--gold-bucket", default="pinaka-gold")
    gold.add_argument("--endpoint-url", default="http://localhost:4566")
    gold.add_argument("--region", default="ap-south-1")
    gold.add_argument("--lookback-days", type=int, default=60)

    gold_range = subparsers.add_parser("gold-range", help="Compute gold features for a date range")
    gold_range.add_argument("--dataset", choices=GOLD_DATASETS, default="bhavcopy_eq")
    gold_range.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    gold_range.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    gold_range.add_argument("--bronze-bucket", default="pinaka-bronze")
    gold_range.add_argument("--gold-bucket", default="pinaka-gold")
    gold_range.add_argument("--endpoint-url", default="http://localhost:4566")
    gold_range.add_argument("--region", default="ap-south-1")
    gold_range.add_argument("--lookback-days", type=int, default=60)
    gold_range.add_argument("--max-workers", type=int, default=4)
    gold_range.add_argument("--continue-on-error", action="store_true")

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
        return

    if args.command == "gold":
        fn = compute_fo_oi_features_for_date if args.dataset == "fo_oi" else compute_features_for_date
        kwargs = dict(
            trade_date=parse_date(args.trade_date),
            dataset=args.dataset,
            bronze_bucket=args.bronze_bucket,
            gold_bucket=args.gold_bucket,
            endpoint_url=args.endpoint_url,
            region_name=args.region,
        )
        if args.dataset == "bhavcopy_eq":
            kwargs["lookback_days"] = args.lookback_days
        result = fn(**kwargs)
        print(json.dumps(result, indent=2, default=str))
        return

    if args.command == "gold-range":
        start = parse_date(args.start_date)
        end = parse_date(args.end_date)
        fn = compute_fo_oi_features_for_date if args.dataset == "fo_oi" else compute_features_for_date

        from concurrent.futures import ThreadPoolExecutor, as_completed

        all_dates: list[date] = []
        cursor = start
        while cursor <= end:
            all_dates.append(cursor)
            cursor += timedelta(days=1)

        results: list[dict] = []
        failures: list[dict] = []
        with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
            future_map = {}
            for d in all_dates:
                kwargs = dict(
                    trade_date=d,
                    dataset=args.dataset,
                    bronze_bucket=args.bronze_bucket,
                    gold_bucket=args.gold_bucket,
                    endpoint_url=args.endpoint_url,
                    region_name=args.region,
                )
                if args.dataset == "bhavcopy_eq":
                    kwargs["lookback_days"] = args.lookback_days
                future_map[pool.submit(fn, **kwargs)] = d

            for fut in as_completed(future_map):
                d = future_map[fut]
                try:
                    result = fut.result()
                    results.append(result)
                except Exception as exc:
                    failures.append({"trade_date": d.isoformat(), "error": str(exc)})
                    if not args.continue_on_error:
                        raise RuntimeError(
                            f"Gold computation failed on {d.isoformat()} "
                            f"({len(results)}/{len(all_dates)}). "
                            "Re-run with --continue-on-error to skip failing dates."
                        ) from exc

        results.sort(key=lambda r: r.get("trade_date", ""))
        print(json.dumps({
            "dataset": args.dataset,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "max_workers": args.max_workers,
            "dates_requested": len(all_dates),
            "dates_succeeded": len(results),
            "dates_failed": len(failures),
            "failures": failures,
            "results": results,
        }, indent=2, default=str))
        return


if __name__ == "__main__":
    main()
