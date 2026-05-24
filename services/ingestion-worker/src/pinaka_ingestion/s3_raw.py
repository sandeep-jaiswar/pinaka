from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from uuid import uuid4

import polars as pl
from pinaka_common.cloud import list_all_keys, new_s3_client


def build_raw_object_key(dataset: str, trade_date: str, run_id: str) -> str:
    return f"nse/{dataset}/dt={trade_date}/run_id={run_id}/part-00000.json"


def generate_run_id() -> str:
    return uuid4().hex


def current_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _s3_client(*, endpoint_url: str, region_name: str):
    return new_s3_client(endpoint_url=endpoint_url, region_name=region_name)


def put_payload_json(
    *,
    bucket: str,
    key: str,
    payload: dict,
    endpoint_url: str,
    region_name: str,
) -> str:
    client = _s3_client(endpoint_url=endpoint_url, region_name=region_name)

    body = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), default=str).encode("utf-8")
    client.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/json")
    return f"s3://{bucket}/{key}"


def put_payload_parquet(
    *,
    bucket: str,
    key: str,
    df: pl.DataFrame,
    endpoint_url: str,
    region_name: str,
) -> str:
    client = _s3_client(endpoint_url=endpoint_url, region_name=region_name)
    buf = io.BytesIO()
    df.write_parquet(buf)
    buf.seek(0)
    client.put_object(Bucket=bucket, Key=key, Body=buf, ContentType="application/octet-stream")
    return f"s3://{bucket}/{key}"


def list_raw_partition_keys(
    *,
    bucket: str,
    dataset: str,
    trade_date: str,
    endpoint_url: str,
    region_name: str,
) -> list[str]:
    client = _s3_client(endpoint_url=endpoint_url, region_name=region_name)
    prefix = f"nse/{dataset}/dt={trade_date}/"
    return list_all_keys(client, bucket, prefix)
