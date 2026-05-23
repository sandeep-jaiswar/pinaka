from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import polars as pl

from ..s3_raw import _s3_client

_DEFAULT_DB_PATH = Path("/tmp/pinaka.duckdb")

_BRONZE_DATASETS = [
    "bhavcopy_eq",
    "fo_oi",
    "corp_actions",
    "index_constituents",
    "block_deals",
]


def _configure_s3(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("INSTALL httpfs")
    con.execute("LOAD httpfs")
    con.execute("SET s3_endpoint='ministack:4566'")
    con.execute("SET s3_use_ssl=false")
    con.execute("SET s3_access_key_id='test'")
    con.execute("SET s3_secret_access_key='test'")
    con.execute("SET s3_url_style='path'")
    con.execute("SET s3_region='ap-south-1'")


def _s3_path(bucket: str, prefix: str) -> str:
    return f"s3://{bucket}/{prefix}"


def _check_has_data(dataset: str, bucket: str, endpoint_url: str, region_name: str) -> bool:
    client = _s3_client(endpoint_url=endpoint_url, region_name=region_name)
    prefix = f"nse/{dataset}/"
    token = None
    while True:
        kwargs = dict(Bucket=bucket, Prefix=prefix, MaxKeys=100)
        if token:
            kwargs["ContinuationToken"] = token
        resp = client.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            if obj["Key"].endswith(".parquet"):
                return True
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    return False


def _create_bronze_view(
    con: duckdb.DuckDBPyConnection,
    dataset: str,
    bucket: str,
    endpoint_url: str,
    region_name: str,
) -> None:
    view_name = f"bronze_{dataset.replace('-', '_')}"
    pattern = _s3_path(bucket, f"nse/{dataset}/**/part-00000.parquet")

    if not _check_has_data(dataset, bucket, endpoint_url, region_name):
        con.execute(f"CREATE OR REPLACE VIEW {view_name} AS SELECT NULL::VARCHAR AS _empty WHERE FALSE")
        return

    con.execute(
        f"CREATE OR REPLACE VIEW {view_name} AS "
        f"SELECT * FROM read_parquet('{pattern}', hive_partitioning=true)"
    )


def _list_views(con: duckdb.DuckDBPyConnection) -> set[str]:
    rows = con.execute("SELECT table_name FROM information_schema.views WHERE table_schema='main'").fetchall()
    return {r[0] for r in rows}


def get_connection(
    *,
    bronze_bucket: str = "pinaka-bronze",
    endpoint_url: str = "http://ministack:4566",
    region_name: str = "ap-south-1",
    db_path: Path = _DEFAULT_DB_PATH,
) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(db_path))
    _configure_s3(con)

    existing = _list_views(con)
    expected = {f"bronze_{ds.replace('-', '_')}" for ds in _BRONZE_DATASETS}
    if not expected.issubset(existing):
        for ds in _BRONZE_DATASETS:
            _create_bronze_view(con, ds, bronze_bucket, endpoint_url, region_name)

    return con


def query(
    sql: str,
    db_path: Path = _DEFAULT_DB_PATH,
) -> pl.DataFrame:
    con = get_connection(db_path=db_path)
    result = con.execute(sql).pl()
    con.close()
    return result
