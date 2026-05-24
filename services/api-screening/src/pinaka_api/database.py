from __future__ import annotations

import re
from contextlib import contextmanager
from typing import Any, Generator

import duckdb
import polars as pl

from .config import settings

_SAFE_CONFIG_RE = re.compile(r"^[a-zA-Z0-9_.:/@\-\+]+$")


def _safe(value: str) -> str:
    if not _SAFE_CONFIG_RE.match(value):
        raise ValueError(f"Unsafe config value: {value!r}")
    return value


def _configure_s3(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("INSTALL httpfs")
    con.execute("LOAD httpfs")
    con.execute(f"SET s3_endpoint='{_safe(settings.s3_endpoint)}'")
    con.execute(f"SET s3_use_ssl={'true' if settings.s3_use_ssl else 'false'}")
    con.execute(f"SET s3_access_key_id='{_safe(settings.s3_access_key)}'")
    con.execute(f"SET s3_secret_access_key='{_safe(settings.s3_secret_key)}'")
    con.execute(f"SET s3_url_style='{_safe(settings.s3_url_style)}'")
    con.execute(f"SET s3_region='{_safe(settings.s3_region)}'")


def _ensure_bronze_views(con: duckdb.DuckDBPyConnection) -> None:
    datasets = [
        "bhavcopy_eq",
        "fo_oi",
        "corp_actions",
        "index_constituents",
        "block_deals",
    ]
    for ds in datasets:
        view_name = f"bronze_{ds.replace('-', '_')}"
        pattern = f"s3://{settings.bronze_bucket}/nse/{ds}/**/part-00000.parquet"
        try:
            con.execute(
                f"CREATE OR REPLACE VIEW {view_name} AS "
                f"SELECT * FROM read_parquet('{pattern}', hive_partitioning=true)"
            )
        except Exception:
            con.execute(
                f"CREATE OR REPLACE VIEW {view_name} AS "
                f"SELECT NULL::VARCHAR AS _empty WHERE FALSE"
            )


@contextmanager
def get_connection() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    con = duckdb.connect(settings.db_path)
    try:
        _configure_s3(con)
        _ensure_bronze_views(con)
        yield con
    finally:
        con.close()


def query(sql: str) -> pl.DataFrame:
    with get_connection() as con:
        return con.execute(sql).pl()


def query_rows(sql: str) -> list[dict[str, Any]]:
    with get_connection() as con:
        result = con.execute(sql)
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]
