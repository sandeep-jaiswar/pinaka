from __future__ import annotations

from datetime import date
from uuid import uuid4

import polars as pl

from ..s3_raw import (
    put_payload_parquet,
)


_BRONZE_COLUMN_MAP: dict[str, dict[str, str]] = {
    "bhavcopy_eq": {
        "symbol": "symbol",
        "series": "series",
        "DATE1": "trade_date",
        "prev_close": "prev_close",
        "open_price": "open",
        "high_price": "high",
        "low_price": "low",
        "last_price": "last",
        "close_price": "close",
        "ttl_trd_qnty": "totaltradedquantity",
        "turnover_lacs": "totaltradedvalue",
        "PREV_CLOSE": "prev_close",
        "OPEN_PRICE": "open",
        "HIGH_PRICE": "high",
        "LOW_PRICE": "low",
        "LAST_PRICE": "last",
        "CLOSE_PRICE": "close",
        "AVG_PRICE": "avg_price",
        "TTL_TRD_QNTY": "totaltradedquantity",
        "TURNOVER_LACS": "totaltradedvalue",
        "NO_OF_TRADES": "no_of_trades",
        "DELIV_QTY": "deliv_qty",
        "DELIV_PER": "deliv_per",
    },
    "corp_actions": {
        "symbol": "symbol",
        "exDate": "ex_date",
        "subject": "purpose",
        "faceVal": "face_value",
        "recDate": "record_date",
        "bcStartDate": "bc_start_date",
        "bcEndDate": "bc_end_date",
    },
    "index_constituents": {
        "symbol": "symbol",
        "company_name": "company_name",
        "index_name": "index_name",
        "weight_percentage": "weight_percentage",
        "industry": "industry",
        "trade_date": "trade_date",
    },
    "fo_oi": {
        "Client Type": "client_type",
        "client_type": "client_type",
        "Future Index Long": "future_index_long",
        "future_index_long": "future_index_long",
        "Future Index Short": "future_index_short",
        "future_index_short": "future_index_short",
        "Future Stock Long": "future_stock_long",
        "future_stock_long": "future_stock_long",
        "Future Stock Short       ": "future_stock_short",
        "Future Stock Short": "future_stock_short",
        "future_stock_short": "future_stock_short",
        "Option Index Call Long": "option_index_call_long",
        "option_index_call_long": "option_index_call_long",
        "Option Index Put Long": "option_index_put_long",
        "option_index_put_long": "option_index_put_long",
        "Option Index Call Short": "option_index_call_short",
        "option_index_call_short": "option_index_call_short",
        "Option Index Put Short": "option_index_put_short",
        "option_index_put_short": "option_index_put_short",
        "Option Stock Call Long": "option_stock_call_long",
        "option_stock_call_long": "option_stock_call_long",
        "Option Stock Put Long": "option_stock_put_long",
        "option_stock_put_long": "option_stock_put_long",
        "Option Stock Call Short": "option_stock_call_short",
        "option_stock_call_short": "option_stock_call_short",
        "Option Stock Put Short": "option_stock_put_short",
        "option_stock_put_short": "option_stock_put_short",
        "Total Long Contracts      ": "total_long_contracts",
        "Total Long Contracts": "total_long_contracts",
        "total_long_contracts": "total_long_contracts",
        "Total Short Contracts": "total_short_contracts",
        "total_short_contracts": "total_short_contracts",
        "trade_date": "trade_date",
    },
    "block_deals": {
        "Symbol": "symbol",
        "symbol": "symbol",
        "ClientName": "client_name",
        "client_name": "client_name",
        "Buy/Sell": "deal_type",
        "buy_sell": "deal_type",
        "QuantityTraded": "quantity",
        "quantity_traded": "quantity",
        "TradePrice/Wght.Avg.Price": "price",
        "tradeprice_wght_avg_price": "price",
    },
}

_BRONZE_ALLOWED_FIELDS: dict[str, set[str]] = {
    ds: set(m.values()) for ds, m in _BRONZE_COLUMN_MAP.items()
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
    column_map = _BRONZE_COLUMN_MAP.get(dataset, {})
    allowed = _BRONZE_ALLOWED_FIELDS.get(dataset)
    clean: dict = {}
    for raw_key, value in record.items():
        norm_key = raw_key.strip().lower().replace(" ", "_").replace("-", "_")
        canonical = column_map.get(raw_key) or column_map.get(norm_key)
        if canonical is None:
            continue
        if allowed and canonical not in allowed:
            continue
        clean[canonical] = _normalize_field(value)
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
    object_key = f"nse/{dataset}/dt={trade_date}/run_id={run_id}/part-00000.parquet"

    row_count = len(normalized)
    s3_uri = None
    if row_count > 0:
        df = pl.DataFrame(normalized)
        s3_uri = put_payload_parquet(
            bucket=bucket,
            key=object_key,
            df=df,
            endpoint_url=endpoint_url,
            region_name=region_name,
        )

    return {
        "dataset": dataset,
        "trade_date": trade_date,
        "row_count": row_count,
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
