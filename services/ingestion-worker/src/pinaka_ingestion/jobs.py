from __future__ import annotations

from datetime import date, timedelta

from .nse_client import PullRequest, fetch_bhavcopy_eq, fetch_dataset
from .s3_raw import (
    build_raw_object_key,
    current_utc_iso,
    generate_run_id,
    list_raw_partition_keys,
    put_payload_json,
)
from .state_store import build_chunks


def backfill_plan(dataset: str, start_date: date, end_date: date, chunk_days: int) -> list[dict]:
    chunks = build_chunks(start_date, end_date, chunk_days)
    return [
        {
            "dataset": dataset,
            "chunk_start": chunk.start_date.isoformat(),
            "chunk_end": chunk.end_date.isoformat(),
        }
        for chunk in chunks
    ]


def run_one_chunk(dataset: str, chunk_start: date, chunk_end: date) -> dict:
    request = PullRequest(dataset=dataset, start_date=chunk_start, end_date=chunk_end)
    return fetch_dataset(request)


def ingest_bhavcopy_eq_for_date(
    *,
    trade_date: date,
    bucket: str,
    endpoint_url: str,
    region_name: str,
    dry_run: bool,
    allow_reingest: bool,
) -> dict:
    trade_date_iso = trade_date.isoformat()
    existing_keys = list_raw_partition_keys(
        bucket=bucket,
        dataset="bhavcopy_eq",
        trade_date=trade_date_iso,
        endpoint_url=endpoint_url,
        region_name=region_name,
    )

    if existing_keys and not allow_reingest:
        return {
            "dataset": "bhavcopy_eq",
            "trade_date": trade_date_iso,
            "row_count": 0,
            "bucket": bucket,
            "object_key": None,
            "s3_uri": None,
            "dry_run": dry_run,
            "skipped": True,
            "skip_reason": "partition_exists",
            "existing_objects": len(existing_keys),
        }

    run_id = generate_run_id()
    extract_result = fetch_bhavcopy_eq(trade_date)
    object_key = build_raw_object_key(dataset="bhavcopy_eq", trade_date=trade_date_iso, run_id=run_id)

    payload = {
        "dataset": "bhavcopy_eq",
        "trade_date": trade_date_iso,
        "extracted_at_utc": current_utc_iso(),
        "run_id": run_id,
        "source": "nselib",
        "source_function": extract_result.get("source_function"),
        "row_count": extract_result.get("row_count", 0),
        "records": extract_result.get("records", []),
    }

    s3_uri = None
    if not dry_run:
        s3_uri = put_payload_json(
            bucket=bucket,
            key=object_key,
            payload=payload,
            endpoint_url=endpoint_url,
            region_name=region_name,
        )

    return {
        "dataset": "bhavcopy_eq",
        "trade_date": trade_date_iso,
        "row_count": payload["row_count"],
        "bucket": bucket,
        "object_key": object_key,
        "s3_uri": s3_uri,
        "dry_run": dry_run,
        "skipped": False,
        "existing_objects": len(existing_keys),
    }


def ingest_bhavcopy_eq_range(
    *,
    start_date: date,
    end_date: date,
    chunk_days: int,
    bucket: str,
    endpoint_url: str,
    region_name: str,
    dry_run: bool,
    continue_on_error: bool,
    allow_reingest: bool,
) -> dict:
    chunks = build_chunks(start_date, end_date, chunk_days)
    results: list[dict] = []
    failures: list[dict] = []

    for chunk in chunks:
        trade_date = chunk.start_date
        while trade_date <= chunk.end_date:
            try:
                day_result = ingest_bhavcopy_eq_for_date(
                    trade_date=trade_date,
                    bucket=bucket,
                    endpoint_url=endpoint_url,
                    region_name=region_name,
                    dry_run=dry_run,
                    allow_reingest=allow_reingest,
                )
                results.append(day_result)
            except Exception as exc:
                error_entry = {
                    "trade_date": trade_date.isoformat(),
                    "error": str(exc),
                }
                failures.append(error_entry)
                if not continue_on_error:
                    raise RuntimeError(
                        f"Range ingestion failed on {trade_date.isoformat()}. "
                        "Re-run with --continue-on-error to skip failing dates."
                    ) from exc

            trade_date += timedelta(days=1)

    total_rows = sum(item.get("row_count", 0) for item in results)
    return {
        "dataset": "bhavcopy_eq",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "chunk_days": chunk_days,
        "dates_requested": (end_date - start_date).days + 1,
        "dates_succeeded": len(results),
        "dates_failed": len(failures),
        "rows_total": total_rows,
        "dry_run": dry_run,
        "allow_reingest": allow_reingest,
        "failures": failures,
        "results": results,
    }
