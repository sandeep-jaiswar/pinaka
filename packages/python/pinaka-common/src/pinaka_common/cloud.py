from __future__ import annotations

from typing import Any

from pinaka_common.config import settings


def new_s3_client(
    *,
    endpoint_url: str | None = None,
    region_name: str | None = None,
) -> Any:
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url or settings.s3_http_endpoint,
        region_name=region_name or settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )


def list_all_keys(client: Any, bucket: str, prefix: str) -> list[str]:
    keys: list[str] = []
    token: str | None = None
    while True:
        kwargs: dict[str, Any] = dict(Bucket=bucket, Prefix=prefix)
        if token:
            kwargs["ContinuationToken"] = token
        resp = client.list_objects_v2(**kwargs)
        keys.extend(item["Key"] for item in resp.get("Contents", []))
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    return keys
