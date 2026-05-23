from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

from ..s3_raw import _s3_client


_DEFAULT_DB_PATH = Path("/tmp/pinaka.duckdb")


def _fetch_gold_records(
    dataset: str,
    trade_date: date,
    bucket: str,
    endpoint_url: str,
    region_name: str,
) -> pl.DataFrame:
    client = _s3_client(endpoint_url=endpoint_url, region_name=region_name)
    prefix = f"features/{dataset}/dt={trade_date.isoformat()}/"
    resp = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    frames: list[pl.DataFrame] = []
    for obj in resp.get("Contents", []):
        payload = json.loads(
            client.get_object(Bucket=bucket, Key=obj["Key"])["Body"].read().decode("utf-8")
        )
        recs = payload.get("records", [])
        if recs:
            df = pl.DataFrame(recs)
            df = df.with_columns([
                pl.lit(dataset).alias("_dataset"),
                pl.lit(trade_date.isoformat()).alias("_partition_date"),
            ])
            frames.append(df)
    return pl.concat(frames) if frames else pl.DataFrame()


def _fetch_bronze_records(
    dataset: str,
    trade_date: date,
    bucket: str,
    endpoint_url: str,
    region_name: str,
) -> pl.DataFrame:
    client = _s3_client(endpoint_url=endpoint_url, region_name=region_name)
    prefix = f"nse/{dataset}/dt={trade_date.isoformat()}/"
    resp = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    frames: list[pl.DataFrame] = []
    for obj in resp.get("Contents", []):
        payload = json.loads(
            client.get_object(Bucket=bucket, Key=obj["Key"])["Body"].read().decode("utf-8")
        )
        recs = payload.get("records", [])
        if recs:
            df = pl.DataFrame(recs)
            df = df.with_columns([
                pl.lit(dataset).alias("_dataset"),
                pl.lit(trade_date.isoformat()).alias("_partition_date"),
            ])
            frames.append(df)
    return pl.concat(frames) if frames else pl.DataFrame()


def refresh_gold_tables(
    *,
    trade_dates: list[date],
    gold_bucket: str = "pinaka-gold",
    bronze_bucket: str = "pinaka-bronze",
    endpoint_url: str = "http://ministack:4566",
    region_name: str = "ap-south-1",
    db_path: Path = _DEFAULT_DB_PATH,
) -> dict[str, int]:
    con = duckdb.connect(str(db_path))
    totals: dict[str, int] = {}

    gold_datasets = ["bhavcopy_eq", "fo_oi"]
    for ds in gold_datasets:
        frames: list[pl.DataFrame] = []
        for td in trade_dates:
            frames.append(_fetch_gold_records(ds, td, gold_bucket, endpoint_url, region_name))
        df = pl.concat([f for f in frames if f.height > 0]) if frames else pl.DataFrame()
        table_name = f"gold_{ds.replace('-', '_')}"
        con.execute(f"DROP TABLE IF EXISTS {table_name}")
        if df.height > 0:
            con.register("_tmp_df", df)
            con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM _tmp_df")
            con.unregister("_tmp_df")
        totals[f"gold_{ds}"] = df.height

    bronze_datasets = ["bhavcopy_eq", "fo_oi"]
    for ds in bronze_datasets:
        frames: list[pl.DataFrame] = []
        for td in trade_dates:
            frames.append(
                _fetch_bronze_records(ds, td, bronze_bucket, endpoint_url, region_name)
            )
        df = pl.concat([f for f in frames if f.height > 0]) if frames else pl.DataFrame()
        table_name = f"bronze_{ds.replace('-', '_')}"
        con.execute(f"DROP TABLE IF EXISTS {table_name}")
        if df.height > 0:
            con.register("_tmp_df", df)
            con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM _tmp_df")
            con.unregister("_tmp_df")
        totals[f"bronze_{ds}"] = df.height

    con.close()
    return totals


def query(sql: str, db_path: Path = _DEFAULT_DB_PATH) -> pl.DataFrame:
    con = duckdb.connect(str(db_path))
    result = con.execute(sql).pl()
    con.close()
    return result
