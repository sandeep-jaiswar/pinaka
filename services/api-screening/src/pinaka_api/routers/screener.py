from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ..database import query_rows

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.get("/query")
def screener_query(
    min_price: float | None = Query(None, alias="minPrice"),
    max_price: float | None = Query(None, alias="maxPrice"),
    min_volume: float | None = Query(None, alias="minVolume"),
    min_rsi: float | None = Query(None, alias="minRsi"),
    max_rsi: float | None = Query(None, alias="maxRsi"),
    above_sma: bool | None = Query(None, alias="aboveSma"),
    macd_bullish: bool | None = Query(None, alias="macdBullish"),
    index_name: str | None = Query(None, alias="indexName"),
    limit: int = Query(50, alias="limit"),
) -> list[dict[str, Any]]:
    latest = query_rows(
        "SELECT MAX(trade_date) as trade_date FROM bronze_bhavcopy_eq"
    )
    latest_date = latest[0]["trade_date"] if latest else None
    if not latest_date:
        return []

    conditions = [f"b.trade_date = '{latest_date}'"]
    if min_price is not None:
        conditions.append(f"b.close >= {min_price}")
    if max_price is not None:
        conditions.append(f"b.close <= {max_price}")
    if min_volume is not None:
        conditions.append(f"b.totaltradedquantity >= {min_volume}")

    if any([min_rsi is not None, max_rsi is not None, above_sma is not None, macd_bullish is not None]):
        if min_rsi is not None:
            conditions.append(f"f.rsi_14 >= {min_rsi}")
        if max_rsi is not None:
            conditions.append(f"f.rsi_14 <= {max_rsi}")
        if above_sma is not None:
            op = ">" if above_sma else "<"
            conditions.append(f"b.close {op} f.sma_20")
        if macd_bullish is not None:
            if macd_bullish:
                conditions.append("f.macd > f.macd_signal")
            else:
                conditions.append("f.macd < f.macd_signal")

        where_clause = " AND ".join(conditions)
        sql = (
            f"SELECT b.symbol, b.close, b.open, b.high, b.low, "
            f"b.totaltradedquantity, b.deliv_per, "
            f"f.rsi_14, f.sma_20, f.ema_20, f.macd, f.macd_signal, f.macd_histogram "
            f"FROM bronze_bhavcopy_eq b "
            f"INNER JOIN bronze_bhavcopy_eq_features f "
            f"ON b.symbol = f.symbol AND b.trade_date = f.trade_date "
            f"WHERE {where_clause} "
            f"ORDER BY b.totaltradedquantity DESC NULLS LAST "
            f"LIMIT {limit}"
        )
    else:
        where_clause = " AND ".join(conditions)
        sql = (
            f"SELECT b.symbol, b.close, b.open, b.high, b.low, "
            f"b.totaltradedquantity, b.deliv_per "
            f"FROM bronze_bhavcopy_eq b "
            f"WHERE {where_clause} "
            f"ORDER BY b.totaltradedquantity DESC NULLS LAST "
            f"LIMIT {limit}"
        )

    return query_rows(sql)


@router.get("/sectors")
def screener_sectors() -> list[dict[str, Any]]:
    return query_rows(
        "SELECT DISTINCT industry FROM bronze_index_constituents "
        "WHERE industry IS NOT NULL ORDER BY industry"
    )
