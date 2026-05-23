from __future__ import annotations

import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

import polars as pl

from ..s3_raw import _s3_client, current_utc_iso, put_payload_json


def _collect_bronze_range(
    *,
    dataset: str,
    start_date: date,
    end_date: date,
    bucket: str,
    endpoint_url: str,
    region_name: str,
    max_workers: int = 8,
) -> list[dict]:
    client = _s3_client(endpoint_url=endpoint_url, region_name=region_name)
    all_keys: list[tuple[str, str]] = []

    cursor = start_date
    while cursor <= end_date:
        prefix = f"nse/{dataset}/dt={cursor.isoformat()}/"
        token = None
        while True:
            kwargs = dict(Bucket=bucket, Prefix=prefix)
            if token:
                kwargs["ContinuationToken"] = token
            resp = client.list_objects_v2(**kwargs)
            for item in resp.get("Contents", []):
                if item["Key"].endswith(".parquet"):
                    all_keys.append((item["Key"], cursor.isoformat()))
            if not resp.get("IsTruncated"):
                break
            token = resp.get("NextContinuationToken")
        cursor += timedelta(days=1)

    all_records: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {}
        for key, dt_str in all_keys:
            fut = pool.submit(_download_s3_parquet, client, bucket, key)
            futures[fut] = dt_str

        for fut in as_completed(futures):
            dt_str = futures[fut]
            try:
                records = fut.result()
                for r in records:
                    r["trade_date"] = dt_str
                all_records.extend(records)
            except Exception:
                pass

    return all_records


def _download_s3_parquet(client, bucket: str, key: str) -> list[dict]:
    obj = client.get_object(Bucket=bucket, Key=key)
    buf = io.BytesIO(obj["Body"].read())
    return pl.read_parquet(buf).to_dicts()


def compute_fo_oi_features_for_date(
    *,
    trade_date: date,
    dataset: str = "fo_oi",
    bronze_bucket: str = "pinaka-bronze",
    gold_bucket: str = "pinaka-gold",
    endpoint_url: str = "http://ministack:4566",
    region_name: str = "ap-south-1",
) -> dict:
    raw = _collect_bronze_range(
        dataset=dataset,
        start_date=trade_date,
        end_date=trade_date,
        bucket=bronze_bucket,
        endpoint_url=endpoint_url,
        region_name=region_name,
    )

    if not raw:
        return {"dataset": dataset, "trade_date": trade_date.isoformat(), "records": 0}

    df = pl.DataFrame(raw)

    needed = {"client_type", "future_index_long", "future_index_short",
              "future_stock_long", "future_stock_short",
              "option_index_call_long", "option_index_put_long",
              "option_index_call_short", "option_index_put_short",
              "option_stock_call_long", "option_stock_put_long",
              "option_stock_call_short", "option_stock_put_short",
              "total_long_contracts", "total_short_contracts"}
    if not needed.issubset(set(df.columns)):
        return {"dataset": dataset, "trade_date": trade_date.isoformat(), "records": 0}

    num_cols = [c for c in df.columns if c not in ("client_type", "trade_date")]
    for c in num_cols:
        df = df.with_columns(pl.col(c).cast(pl.Float64).fill_nan(None))

    df = df.with_columns([
        (pl.col("future_index_long") + pl.col("future_stock_long")
         - pl.col("future_index_short") - pl.col("future_stock_short")).alias("net_futures"),
        (pl.col("option_index_call_long") + pl.col("option_stock_call_long")
         + pl.col("option_index_put_long") + pl.col("option_stock_put_long")
         - pl.col("option_index_call_short") - pl.col("option_stock_call_short")
         - pl.col("option_index_put_short") - pl.col("option_stock_put_short")).alias("net_options"),
        (pl.col("total_long_contracts") - pl.col("total_short_contracts")).alias("net_total"),
        (pl.col("total_long_contracts") / pl.col("total_short_contracts").clip(1)).alias("long_short_ratio"),
        ((pl.col("option_index_put_long") + pl.col("option_stock_put_long"))
         / (pl.col("option_index_call_long") + pl.col("option_stock_call_long")).clip(1)).alias("put_call_ratio"),
    ])

    records = df.to_dicts()
    for r in records:
        for k, v in r.items():
            if isinstance(v, float | int) and v != v:
                r[k] = None
        r["trade_date"] = trade_date.isoformat()

    run_id = uuid4().hex
    object_key = f"features/{dataset}/dt={trade_date.isoformat()}/run_id={run_id}/features.json"

    payload = {
        "dataset": dataset,
        "trade_date": trade_date.isoformat(),
        "gold_at_utc": current_utc_iso(),
        "run_id": run_id,
        "records": len(records),
        "records": records,
    }

    s3_uri = put_payload_json(
        bucket=gold_bucket, key=object_key, payload=payload,
        endpoint_url=endpoint_url, region_name=region_name,
    )

    return {
        "dataset": dataset,
        "trade_date": trade_date.isoformat(),
        "records": len(records),
        "bucket": gold_bucket,
        "object_key": object_key,
        "s3_uri": s3_uri,
        "run_id": run_id,
    }


def compute_features_for_date(
    *,
    trade_date: date,
    dataset: str = "bhavcopy_eq",
    bronze_bucket: str = "pinaka-bronze",
    gold_bucket: str = "pinaka-gold",
    endpoint_url: str = "http://ministack:4566",
    region_name: str = "ap-south-1",
    lookback_days: int = 30,
) -> dict:
    start_date = trade_date - timedelta(days=lookback_days)

    raw = _collect_bronze_range(
        dataset=dataset,
        start_date=start_date,
        end_date=trade_date,
        bucket=bronze_bucket,
        endpoint_url=endpoint_url,
        region_name=region_name,
    )

    if not raw:
        return {
            "dataset": dataset,
            "trade_date": trade_date.isoformat(),
            "symbols": 0,
        }

    df = pl.DataFrame(raw)

    str_cols = [s for s in ["symbol", "trade_date"] if s in df.columns]
    num_cols = [s for s in ["close", "high", "low", "totaltradedquantity", "volume", "open"] if s in df.columns]

    df = df.with_columns([
        pl.col(c).cast(pl.Utf8).alias(c) for c in str_cols
    ])
    for c in num_cols:
        df = df.with_columns(
            pl.col(c).cast(pl.Float64).fill_nan(None).alias(c)
        )

    if df.height == 0 or "symbol" not in df.columns or "close" not in df.columns:
        return {
            "dataset": dataset,
            "trade_date": trade_date.isoformat(),
            "symbols": 0,
        }

    df = df.sort(["symbol", "trade_date"])

    df = df.with_columns([
        pl.col("close").rolling_mean(window_size=20, min_periods=1).over("symbol").alias("sma_20"),
        pl.col("close").ewm_mean(span=20, adjust=False).over("symbol").alias("ema_20"),
    ])

    df = df.with_columns(
        pl.col("close").diff().over("symbol").alias("_price_change")
    )

    df = df.with_columns([
        pl.when(pl.col("_price_change") > 0)
        .then(pl.col("_price_change"))
        .otherwise(0)
        .over("symbol")
        .alias("_gain"),
        pl.when(pl.col("_price_change") < 0)
        .then(-pl.col("_price_change"))
        .otherwise(0)
        .over("symbol")
        .alias("_loss"),
    ])

    df = df.with_columns([
        pl.col("_gain").ewm_mean(alpha=1 / 14, adjust=False).over("symbol").alias("_avg_gain"),
        pl.col("_loss").ewm_mean(alpha=1 / 14, adjust=False).over("symbol").alias("_avg_loss"),
    ])

    df = df.with_columns(
        (100.0 - 100.0 / (1.0 + pl.col("_avg_gain") / pl.col("_avg_loss").clip(1e-10))).alias("rsi_14")
    )

    df = df.with_columns([
        pl.col("close").ewm_mean(span=12, adjust=False).over("symbol").alias("_ema_12"),
        pl.col("close").ewm_mean(span=26, adjust=False).over("symbol").alias("_ema_26"),
    ])

    df = df.with_columns(
        (pl.col("_ema_12") - pl.col("_ema_26")).alias("macd")
    )

    df = df.with_columns(
        pl.col("macd").ewm_mean(span=9, adjust=False).over("symbol").alias("macd_signal")
    )

    df = df.with_columns(
        (pl.col("macd") - pl.col("macd_signal")).alias("macd_histogram")
    )

    target = df.filter(pl.col("trade_date") == trade_date.isoformat())

    records = target.select([
        "symbol",
        "trade_date",
        "close",
        "totaltradedquantity",
        "sma_20",
        "ema_20",
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_histogram",
    ]).to_dicts()

    for r in records:
        for k, v in r.items():
            if isinstance(v, float | int) and v != v:
                r[k] = None

    run_id = uuid4().hex
    object_key = f"features/{dataset}/dt={trade_date.isoformat()}/run_id={run_id}/features.json"

    payload = {
        "dataset": dataset,
        "trade_date": trade_date.isoformat(),
        "gold_at_utc": current_utc_iso(),
        "run_id": run_id,
        "symbols": len(records),
        "records": records,
    }

    s3_uri = put_payload_json(
        bucket=gold_bucket,
        key=object_key,
        payload=payload,
        endpoint_url=endpoint_url,
        region_name=region_name,
    )

    return {
        "dataset": dataset,
        "trade_date": trade_date.isoformat(),
        "symbols": len(records),
        "bucket": gold_bucket,
        "object_key": object_key,
        "s3_uri": s3_uri,
        "run_id": run_id,
    }
