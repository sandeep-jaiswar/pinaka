from __future__ import annotations

from datetime import date
from uuid import uuid4

from ..s3_raw import (
    current_utc_iso,
    put_payload_json,
)


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
        "trade_date",
    },
    "index_constituents": {
        "symbol", "company_name", "index_name", "weight_percentage",
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


def _normalize_field(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return value

    if isinstance(value, str):
        stripped = value.strip()
        if stripped in ("", "-"):
            return None
        return stripped

    return value


def _normalize_record(dataset: str, record: dict) -> dict:
    expected_fields = _BRONZE_SCHEMAS.get(dataset, set())
    clean: dict = {}
    for raw_key, value in record.items():
        key = raw_key.strip().lower().replace(" ", "_").replace("-", "_")
        if expected_fields and key not in expected_fields:
            continue
        clean[key] = _normalize_field(value)
    return clean


def normalize_to_bronze(
    *,
    dataset: str,
    raw_records: list[dict],
    trade_date: str,
    run_id: str,
    bucket: str = "pinaka-bronze",
    endpoint_url: str = "http://ministack:4566",
    region_name: str = "ap-south-1",
) -> dict:
    normalized = [_normalize_record(dataset, r) for r in raw_records if r]
    object_key = f"nse/{dataset}/dt={trade_date}/run_id={run_id}/bronze.json"

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
        "run_id": run_id,
    }


def bronze_dataset_for_date(
    *,
    dataset: str,
    trade_date: date,
    raw_records: list[dict],
    bucket: str = "pinaka-bronze",
    endpoint_url: str = "http://ministack:4566",
    region_name: str = "ap-south-1",
) -> dict:
    run_id = uuid4().hex
    return normalize_to_bronze(
        dataset=dataset,
        raw_records=raw_records,
        trade_date=trade_date.isoformat(),
        run_id=run_id,
        bucket=bucket,
        endpoint_url=endpoint_url,
        region_name=region_name,
    )
