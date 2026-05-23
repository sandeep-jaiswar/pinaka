from __future__ import annotations

import io
import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import polars as pl


def _s3_client(*, endpoint_url: str, region_name: str):
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=region_name,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )


def build_raw_object_key(dataset: str, trade_date: str, run_id: str) -> str:
    return f"nse/{dataset}/dt={trade_date}/run_id={run_id}/part-00000.json"


def generate_run_id() -> str:
    return uuid4().hex


def current_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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

    keys: list[str] = []
    continuation_token = None

    while True:
        if continuation_token:
            response = client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                ContinuationToken=continuation_token,
            )
        else:
            response = client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
            )

        contents = response.get("Contents", [])
        keys.extend(item["Key"] for item in contents)

        if not response.get("IsTruncated"):
            break
        continuation_token = response.get("NextContinuationToken")

    return keys
