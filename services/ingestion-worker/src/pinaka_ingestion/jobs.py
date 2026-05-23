from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

from .nse_client import EXTRACTORS, NseLibError, PullRequest, RAW_DATASETS
from .s3_raw import (
    build_raw_object_key,
    current_utc_iso,
    generate_run_id,
    list_raw_partition_keys,
    put_payload_json,
)
from .state_store import BackfillChunk, build_chunks


def backfill_plan(dataset: str, start_date: date, end_date: date, chunk_days: int) -> list[dict]:
    if dataset not in EXTRACTORS:
        raise ValueError(f"Unknown dataset: {dataset}. Available: {RAW_DATASETS}")
    chunks = build_chunks(start_date, end_date, chunk_days)
    return [
        {
            "dataset": dataset,
            "chunk_start": chunk.start_date.isoformat(),
            "chunk_end": chunk.end_date.isoformat(),
        }
        for chunk in chunks
    ]


def ingest_dataset_for_date(
    *,
    dataset: str,
    trade_date: date,
    bucket: str,
    endpoint_url: str,
    region_name: str,
    dry_run: bool,
    allow_reingest: bool,
) -> dict:
    trade_date_iso = trade_date.isoformat()

    existing_keys: list[str] = []
    if not allow_reingest:
        existing_keys = list_raw_partition_keys(
            bucket=bucket,
            dataset=dataset,
            trade_date=trade_date_iso,
            endpoint_url=endpoint_url,
            region_name=region_name,
        )

    if existing_keys and not allow_reingest:
        return {
            "dataset": dataset,
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
    request = PullRequest(dataset=dataset, start_date=trade_date, end_date=trade_date)
    extract_result = EXTRACTORS[dataset](trade_date)
    row_count = extract_result.get("row_count", 0)

    object_key = build_raw_object_key(dataset=dataset, trade_date=trade_date_iso, run_id=run_id)

    payload = {
        "dataset": dataset,
        "trade_date": trade_date_iso,
        "extracted_at_utc": current_utc_iso(),
        "run_id": run_id,
        "source": "nselib",
        "source_function": extract_result.get("source_function"),
        "row_count": row_count,
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
        "dataset": dataset,
        "trade_date": trade_date_iso,
        "row_count": row_count,
        "bucket": bucket,
        "object_key": object_key,
        "s3_uri": s3_uri,
        "dry_run": dry_run,
        "skipped": False,
        "existing_objects": len(existing_keys),
    }


def ingest_dataset_range(
    *,
    dataset: str,
    start_date: date,
    end_date: date,
    chunk_days: int = 30,
    bucket: str,
    endpoint_url: str,
    region_name: str,
    dry_run: bool = False,
    continue_on_error: bool = False,
    allow_reingest: bool = False,
    max_workers: int | None = None,
) -> dict:
    all_dates: list[date] = []
    cursor = start_date
    while cursor <= end_date:
        all_dates.append(cursor)
        cursor += timedelta(days=1)

    results: list[dict] = []
    failures: list[dict] = []
    completed = 0
    total = len(all_dates)

    if max_workers == 0:
        max_workers = None

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {
            pool.submit(
                ingest_dataset_for_date,
                dataset=dataset,
                trade_date=d,
                bucket=bucket,
                endpoint_url=endpoint_url,
                region_name=region_name,
                dry_run=dry_run,
                allow_reingest=allow_reingest,
            ): d
            for d in all_dates
        }

        for future in as_completed(future_map):
            d = future_map[future]
            completed += 1
            try:
                day_result = future.result()
                results.append(day_result)
            except Exception as exc:
                failures.append({"trade_date": d.isoformat(), "error": str(exc)})
                if not continue_on_error:
                    raise RuntimeError(
                        f"Range ingestion failed on {d.isoformat()} for {dataset} "
                        f"({completed}/{total}). Re-run with --continue-on-error "
                        "to skip failing dates."
                    ) from exc

    results.sort(key=lambda r: r.get("trade_date", ""))
    total_rows = sum(item.get("row_count", 0) for item in results)
    return {
        "dataset": dataset,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "chunk_days": chunk_days,
        "max_workers": max_workers,
        "dates_requested": total,
        "dates_succeeded": len(results),
        "dates_failed": len(failures),
        "rows_total": total_rows,
        "dry_run": dry_run,
        "allow_reingest": allow_reingest,
        "failures": failures,
        "results": results,
    }


_RAW_BRONZE_BUCKET = "pinaka-bronze"


def _bronze_object_key(dataset: str, trade_date: str, run_id: str) -> str:
    return f"nse/{dataset}/dt={trade_date}/run_id={run_id}/bronze.json"


def normalize_to_bronze(
    *,
    dataset: str,
    raw_records: list[dict],
    trade_date: str,
    run_id: str,
    bucket: str,
    endpoint_url: str,
    region_name: str,
) -> dict:
    normalized = _normalize_records(dataset, raw_records)
    object_key = _bronze_object_key(dataset, trade_date, run_id)

    payload = {
        "dataset": dataset,
        "trade_date": trade_date,
        "bronze_at_utc": current_utc_iso(),
        "run_id": run_id,
        "source": "nselib",
        "row_count": len(normalized),
        "records": normalized,
    }

    s3_uri = put_payload_json(
        bucket=bucket,
        key=object_key,
        payload=payload,
        endpoint_url=endpoint_url,
        region_name=region_name,
    )

    return {
        "dataset": dataset,
        "trade_date": trade_date,
        "row_count": len(normalized),
        "bucket": bucket,
        "object_key": object_key,
        "s3_uri": s3_uri,
    }


_BRONZE_SCHEMAS: dict[str, set[str]] = {
    "bhavcopy_eq": {
        "symbol", "series", "open", "high", "low", "close", "last",
        "prevclose", "totaltradedquantity", "totaltradedvalue",
        "timestamp", "trade_date",
    },
    "deliverable_eq": {
        "symbol", "delivered_quantity", "delivery_percentage",
        "total_traded_quantity", "trade_date",
    },
    "corp_actions": {
        "symbol", "ex_date", "purpose", "action_type",
        "face_value", "record_date", "bc_start_date", "bc_end_date",
    },
    "index_constituents": {
        "symbol", "company_name", "index_name", "weight",
        "industry", "trade_date",
    },
    "fo_oi": {
        "symbol", "instrument", "expiry_date", "option_type",
        "strike_price", "open_interest", "change_in_oi",
        "volume", "trade_date",
    },
    "block_deals": {
        "symbol", "client_name", "deal_type", "quantity",
        "price", "value", "trade_date",
    },
}


def _normalize_records(dataset: str, records: list[dict]) -> list[dict]:
    expected_fields = _BRONZE_SCHEMAS.get(dataset, set())
    normalized: list[dict] = []
    for record in records:
        clean = {}
        for key, value in record.items():
            clean_key = key.strip().lower().replace(" ", "_").replace("-", "_")
            if expected_fields and clean_key not in expected_fields:
                continue
            clean[clean_key] = value
        normalized.append(clean)
    return normalized


def normalize_raw_to_bronze_for_date(
    *,
    dataset: str,
    trade_date: date,
    raw_bucket: str = "pinaka-raw",
    bronze_bucket: str = "pinaka-bronze",
    endpoint_url: str = "http://ministack:4566",
    region_name: str = "ap-south-1",
) -> dict:
    from .pipeline.bronze import bronze_dataset_for_date
    from .s3_raw import _s3_client
    import json

    trade_date_iso = trade_date.isoformat()
    client = _s3_client(endpoint_url=endpoint_url, region_name=region_name)
    prefix = f"nse/{dataset}/dt={trade_date_iso}/"
    raw_keys: list[str] = []
    token = None
    while True:
        kwargs = dict(Bucket=raw_bucket, Prefix=prefix)
        if token:
            kwargs["ContinuationToken"] = token
        resp = client.list_objects_v2(**kwargs)
        raw_keys.extend(item["Key"] for item in resp.get("Contents", []))
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")

    if not raw_keys:
        return {"dataset": dataset, "trade_date": trade_date_iso, "row_count": 0, "skipped": True, "skip_reason": "no_raw_data"}

    records: list[dict] = []
    for key in raw_keys:
        obj = client.get_object(Bucket=raw_bucket, Key=key)
        payload = json.loads(obj["Body"].read().decode("utf-8"))
        records.extend(payload.get("records", []))

    result = bronze_dataset_for_date(
        dataset=dataset,
        trade_date=trade_date,
        raw_records=records,
        bucket=bronze_bucket,
        endpoint_url=endpoint_url,
        region_name=region_name,
    )
    result["skipped"] = False
    return result


def normalize_raw_to_bronze_range(
    *,
    dataset: str,
    start_date: date,
    end_date: date,
    raw_bucket: str = "pinaka-raw",
    bronze_bucket: str = "pinaka-bronze",
    endpoint_url: str = "http://ministack:4566",
    region_name: str = "ap-south-1",
    max_workers: int | None = 4,
    continue_on_error: bool = False,
) -> dict:
    all_dates: list[date] = []
    cursor = start_date
    while cursor <= end_date:
        all_dates.append(cursor)
        cursor += timedelta(days=1)

    results: list[dict] = []
    failures: list[dict] = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {
            pool.submit(
                normalize_raw_to_bronze_for_date,
                dataset=dataset,
                trade_date=d,
                raw_bucket=raw_bucket,
                bronze_bucket=bronze_bucket,
                endpoint_url=endpoint_url,
                region_name=region_name,
            ): d
            for d in all_dates
        }

        for fut in as_completed(future_map):
            d = future_map[fut]
            try:
                day_result = fut.result()
                results.append(day_result)
            except Exception as exc:
                failures.append({"trade_date": d.isoformat(), "error": str(exc)})
                if not continue_on_error:
                    raise RuntimeError(
                        f"Bronze normalization failed on {d.isoformat()} for {dataset} "
                        f"({len(results)}/{len(all_dates)}). "
                        "Re-run with --continue-on-error to skip failing dates."
                    ) from exc

    results.sort(key=lambda r: r.get("trade_date", ""))
    total_rows = sum(item.get("row_count", 0) for item in results)
    return {
        "dataset": dataset,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "dates_requested": len(all_dates),
        "dates_succeeded": len(results),
        "dates_failed": len(failures),
        "rows_total": total_rows,
        "failures": failures,
        "results": results,
    }


def ingest_bhavcopy_eq_for_date(**kwargs) -> dict:
    return ingest_dataset_for_date(dataset="bhavcopy_eq", **kwargs)


def ingest_bhavcopy_eq_range(**kwargs) -> dict:
    kwargs.setdefault("dataset", "bhavcopy_eq")
    return ingest_dataset_range(**kwargs)
