from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ..database import query_rows

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("")
def list_symbols(search: str | None = None) -> list[dict[str, Any]]:
    sql = "SELECT DISTINCT symbol, series FROM bronze_bhavcopy_eq WHERE 1=1"
    if search:
        sql += f" AND symbol LIKE '{search.upper()}%'"
    sql += " LIMIT 100"
    return query_rows(sql)


@router.get("/{symbol}")
def stock_detail(symbol: str) -> dict[str, Any]:
    rows = query_rows(
        f"SELECT * FROM bronze_bhavcopy_eq "
        f"WHERE symbol = '{symbol.upper()}' "
        f"ORDER BY trade_date DESC LIMIT 1"
    )
    if not rows:
        raise HTTPException(404, f"Symbol '{symbol}' not found")
    return rows[0]


@router.get("/{symbol}/features")
def stock_features(symbol: str) -> list[dict[str, Any]]:
    return query_rows(
        f"SELECT * FROM bronze_bhavcopy_eq_features "
        f"WHERE symbol = '{symbol.upper()}' "
        f"ORDER BY trade_date DESC LIMIT 1"
    )


@router.get("/{symbol}/history")
def stock_history(
    symbol: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    return query_rows(
        f"SELECT trade_date, open, high, low, close, totaltradedquantity "
        f"FROM bronze_bhavcopy_eq "
        f"WHERE symbol = '{symbol.upper()}' "
        f"ORDER BY trade_date DESC "
        f"LIMIT {limit}"
    )


@router.get("/{symbol}/corp-actions")
def stock_corp_actions(symbol: str) -> list[dict[str, Any]]:
    return query_rows(
        f"SELECT * FROM bronze_corp_actions "
        f"WHERE symbol = '{symbol.upper()}' "
        f"ORDER BY ex_date DESC"
    )


@router.get("/{symbol}/constituents")
def stock_constituents(symbol: str) -> list[dict[str, Any]]:
    return query_rows(
        f"SELECT * FROM bronze_index_constituents "
        f"WHERE symbol = '{symbol.upper()}'"
    )
