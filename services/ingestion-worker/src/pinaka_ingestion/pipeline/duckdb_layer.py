from __future__ import annotations

import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

import duckdb
import polars as pl

from pinaka_common.cloud import list_all_keys
from ..s3_raw import _s3_client

_DEFAULT_DB_PATH = Path("/tmp/pinaka.duckdb")

_S3_ENDPOINT = os.getenv("PINAKA_S3_ENDPOINT", "ministack:4566")
_S3_ACCESS_KEY = os.getenv("PINAKA_AWS_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID", "test")
_S3_SECRET_KEY = os.getenv("PINAKA_AWS_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY", "test")
_S3_REGION = os.getenv("PINAKA_AWS_REGION", "ap-south-1")
_S3_USE_SSL = os.getenv("PINAKA_S3_USE_SSL", "false") == "true"
_S3_URL_STYLE = os.getenv("PINAKA_S3_URL_STYLE", "path")

_BRONZE_DATASETS = [
    "bhavcopy_eq",
    "fo_oi",
    "corp_actions",
    "index_constituents",
    "block_deals",
]

# Allow only safe characters for S3 config values to prevent SQL injection
_SAFE_CONFIG_RE = re.compile(r"^[a-zA-Z0-9_.:/@\-\+]+$")


def _safe_config_value(value: str) -> str:
    if not _SAFE_CONFIG_RE.match(value):
        raise ValueError(f"Unsafe DuckDB config value: {value!r}")
    return value


def _configure_s3(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("INSTALL httpfs")
    con.execute("LOAD httpfs")
    con.execute(f"SET s3_endpoint='{_safe_config_value(_S3_ENDPOINT)}'")
    con.execute(f"SET s3_use_ssl={'true' if _S3_USE_SSL else 'false'}")
    con.execute(f"SET s3_access_key_id='{_safe_config_value(_S3_ACCESS_KEY)}'")
    con.execute(f"SET s3_secret_access_key='{_safe_config_value(_S3_SECRET_KEY)}'")
    con.execute(f"SET s3_url_style='{_safe_config_value(_S3_URL_STYLE)}'")
    con.execute(f"SET s3_region='{_safe_config_value(_S3_REGION)}'")


def _s3_path(bucket: str, prefix: str) -> str:
    return f"s3://{bucket}/{prefix}"


def _check_has_data(dataset: str, bucket: str, endpoint_url: str, region_name: str) -> bool:
    client = _s3_client(endpoint_url=endpoint_url, region_name=region_name)
    prefix = f"nse/{dataset}/"
    for key in list_all_keys(client, bucket, prefix):
        if key.endswith(".parquet"):
            return True
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
    endpoint_url: str | None = None,
    region_name: str | None = None,
    db_path: Path = _DEFAULT_DB_PATH,
) -> duckdb.DuckDBPyConnection:
    if endpoint_url is None:
        endpoint_url = f"http://{_S3_ENDPOINT}"
    if region_name is None:
        region_name = _S3_REGION
    con = duckdb.connect(str(db_path))
    _configure_s3(con)

    existing = _list_views(con)
    expected = {f"bronze_{ds.replace('-', '_')}" for ds in _BRONZE_DATASETS}
    if not expected.issubset(existing):
        for ds in _BRONZE_DATASETS:
            _create_bronze_view(con, ds, bronze_bucket, endpoint_url, region_name)

    return con


@contextmanager
def connect(
    *,
    bronze_bucket: str = "pinaka-bronze",
    endpoint_url: str | None = None,
    region_name: str | None = None,
    db_path: Path = _DEFAULT_DB_PATH,
) -> Generator[duckdb.DuckDBPyConnection, None, None]:
    con = get_connection(
        bronze_bucket=bronze_bucket,
        endpoint_url=endpoint_url,
        region_name=region_name,
        db_path=db_path,
    )
    try:
        yield con
    finally:
        con.close()


def query(
    sql: str,
    db_path: Path = _DEFAULT_DB_PATH,
) -> pl.DataFrame:
    with connect(db_path=db_path) as con:
        return con.execute(sql).pl()
