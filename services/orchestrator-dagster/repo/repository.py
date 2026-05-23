import json
import os
import sys
from datetime import datetime

from dagster import (
    AssetExecutionContext,
    AssetKey,
    Config,
    DailyPartitionsDefinition,
    Definitions,
    asset,
    in_process_executor,
)

# Warm up nselib imports so subprocesses don't pay the cost
import importlib
for mod_name in ("nselib.capital_market", "nselib.derivatives", "nselib.indices"):
    try:
        importlib.import_module(mod_name)
    except ImportError:
        pass

INGESTION_SRC = "/opt/dagster/ingestion-src"
if INGESTION_SRC not in sys.path:
    sys.path.insert(0, INGESTION_SRC)

from pinaka_ingestion.jobs import ingest_dataset_for_date
from pinaka_ingestion.nse_client import RAW_DATASETS
from pinaka_ingestion.pipeline.bronze import bronze_dataset_for_date
from pinaka_ingestion.pipeline.gold import (
    compute_features_for_date,
    compute_fo_oi_features_for_date,
)
from pinaka_ingestion.pipeline.duckdb_layer import get_connection
from pinaka_ingestion.s3_raw import _s3_client

_ENDPOINT_URL = os.getenv("PINAKA_MINISTACK_ENDPOINT", "http://ministack:4566")
_RAW_BUCKET = os.getenv("PINAKA_RAW_BUCKET", "pinaka-raw")
_BRONZE_BUCKET = os.getenv("PINAKA_BRONZE_BUCKET", "pinaka-bronze")
_GOLD_BUCKET = os.getenv("PINAKA_GOLD_BUCKET", "pinaka-gold")
_AWS_REGION = os.getenv("PINAKA_AWS_REGION", "ap-south-1")

daily_partitions = DailyPartitionsDefinition(start_date="2024-01-01")


class DatasetConfig(Config):
    allow_reingest: bool = False


class BronzeConfig(Config):
    bronze_bucket: str = _BRONZE_BUCKET


class GoldConfig(Config):
    gold_bucket: str = _GOLD_BUCKET
    lookback_days: int = 60


def _list_raw_keys(dataset: str, trade_date_iso: str) -> list[str]:
    client = _s3_client(endpoint_url=_ENDPOINT_URL, region_name=_AWS_REGION)
    prefix = f"nse/{dataset}/dt={trade_date_iso}/"
    keys: list[str] = []
    token = None
    while True:
        kwargs = dict(Bucket=_RAW_BUCKET, Prefix=prefix)
        if token:
            kwargs["ContinuationToken"] = token
        resp = client.list_objects_v2(**kwargs)
        keys.extend(item["Key"] for item in resp.get("Contents", []))
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    return keys


def _read_s3_records(bucket: str, keys: list[str]) -> list[dict]:
    client = _s3_client(endpoint_url=_ENDPOINT_URL, region_name=_AWS_REGION)
    records: list[dict] = []
    for key in keys:
        obj = client.get_object(Bucket=bucket, Key=key)
        payload = json.loads(obj["Body"].read().decode("utf-8"))
        records.extend(payload.get("records", []))
    return records


def make_raw_asset(dataset: str):
    @asset(
        name=f"{dataset}_raw",
        partitions_def=daily_partitions,
        kinds={"nse", "s3"},
        description=f"Raw {dataset} data from NSE via nselib, stored in S3",
        group_name="raw",
    )
    def _asset(context: AssetExecutionContext, config: DatasetConfig) -> None:
        trade_date = datetime.strptime(context.partition_key, "%Y-%m-%d").date()
        context.log.info("Ingesting %s for %s", dataset, trade_date)

        result = ingest_dataset_for_date(
            dataset=dataset,
            trade_date=trade_date,
            bucket=_RAW_BUCKET,
            endpoint_url=_ENDPOINT_URL,
            region_name=_AWS_REGION,
            dry_run=False,
            allow_reingest=config.allow_reingest,
        )

        context.log.info(
            "%s/%s: skipped=%s, rows=%s, uri=%s",
            dataset, trade_date,
            result.get("skipped"), result.get("row_count"), result.get("s3_uri"),
        )

    _asset.__name__ = f"{dataset}_raw"
    return _asset


def make_bronze_asset(dataset: str):
    @asset(
        name=f"{dataset}_bronze",
        partitions_def=daily_partitions,
        kinds={"s3"},
        description=f"Bronze normalized {dataset} data",
        group_name="bronze",
        deps=[AssetKey(f"{dataset}_raw")],
    )
    def _asset(context: AssetExecutionContext, config: BronzeConfig) -> None:
        trade_date = datetime.strptime(context.partition_key, "%Y-%m-%d").date()
        trade_date_iso = trade_date.isoformat()

        raw_keys = _list_raw_keys(dataset, trade_date_iso)
        if not raw_keys:
            context.log.warning("No raw keys found for %s/%s, skipping bronze", dataset, trade_date_iso)
            return

        raw_records = _read_s3_records(_RAW_BUCKET, raw_keys)
        context.log.info("Normalizing %s to bronze for %s (%d records)", dataset, trade_date, len(raw_records))

        result = bronze_dataset_for_date(
            dataset=dataset,
            trade_date=trade_date,
            raw_records=raw_records,
            bucket=config.bronze_bucket,
            endpoint_url=_ENDPOINT_URL,
            region_name=_AWS_REGION,
        )

        context.log.info(
            "%s/bronze/%s: rows=%s, uri=%s",
            dataset, trade_date, result.get("row_count"), result.get("s3_uri"),
        )

    _asset.__name__ = f"{dataset}_bronze"
    return _asset


def make_gold_asset(dataset: str):
    @asset(
        name=f"{dataset}_features",
        partitions_def=daily_partitions,
        kinds={"s3"},
        description=f"Gold features computed from {dataset} bronze data",
        group_name="gold",
        deps=[AssetKey(f"{dataset}_bronze")],
    )
    def _asset(context: AssetExecutionContext, config: GoldConfig) -> None:
        trade_date = datetime.strptime(context.partition_key, "%Y-%m-%d").date()

        context.log.info("Computing gold features for %s/%s", dataset, trade_date)

        result = compute_features_for_date(
            trade_date=trade_date,
            dataset=dataset,
            bronze_bucket=_BRONZE_BUCKET,
            gold_bucket=config.gold_bucket,
            endpoint_url=_ENDPOINT_URL,
            region_name=_AWS_REGION,
            lookback_days=config.lookback_days,
        )

        context.log.info(
            "%s/gold/%s: symbols=%s, uri=%s",
            dataset, trade_date, result.get("symbols"), result.get("s3_uri"),
        )

    _asset.__name__ = f"{dataset}_features"
    return _asset


def make_duckdb_asset():
    @asset(
        name="duckdb_refresh",
        kinds={"duckdb", "s3"},
        description="Recreate DuckDB S3-backed views for bronze/gold data",
        group_name="analytics",
    )
    def _asset(context: AssetExecutionContext) -> None:
        context.log.info("Recreating DuckDB S3 views")

        con = get_connection(
            bronze_bucket=_BRONZE_BUCKET,
            endpoint_url=_ENDPOINT_URL,
            region_name=_AWS_REGION,
        )
        views = con.execute(
            "SELECT table_name FROM information_schema.views WHERE table_schema='main'"
        ).fetchall()
        con.close()

        context.log.info("DuckDB views ready: %s", [v[0] for v in views])

    _asset.__name__ = "duckdb_refresh"
    return _asset


def make_fo_oi_gold_asset():
    @asset(
        name="fo_oi_features",
        partitions_def=daily_partitions,
        kinds={"s3"},
        description="Gold OI analytics computed from fo_oi bronze data",
        group_name="gold",
        deps=[AssetKey("fo_oi_bronze")],
    )
    def _asset(context: AssetExecutionContext) -> None:
        trade_date = datetime.strptime(context.partition_key, "%Y-%m-%d").date()

        context.log.info("Computing fo_oi gold features for %s", trade_date)

        result = compute_fo_oi_features_for_date(
            trade_date=trade_date,
            bronze_bucket=_BRONZE_BUCKET,
            gold_bucket=_GOLD_BUCKET,
            endpoint_url=_ENDPOINT_URL,
            region_name=_AWS_REGION,
        )

        context.log.info(
            "fo_oi/gold/%s: records=%s, uri=%s",
            trade_date, result.get("records"), result.get("s3_uri"),
        )

    _asset.__name__ = "fo_oi_features"
    return _asset


raw_assets = [make_raw_asset(ds) for ds in RAW_DATASETS]
bronze_assets = [make_bronze_asset(ds) for ds in RAW_DATASETS]
gold_assets = [make_gold_asset("bhavcopy_eq"), make_fo_oi_gold_asset()]
analytics_assets = [make_duckdb_asset()]

all_assets = [*raw_assets, *bronze_assets, *gold_assets, *analytics_assets]

defs = Definitions(assets=all_assets, executor=in_process_executor)
