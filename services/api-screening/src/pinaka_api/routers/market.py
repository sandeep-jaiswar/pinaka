from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ..database import query_rows

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/latest")
def market_latest() -> dict[str, Any]:
    latest = query_rows(
        "SELECT MAX(trade_date) as trade_date FROM bronze_bhavcopy_eq"
    )
    latest_date = latest[0]["trade_date"] if latest else None

    gainers = query_rows(
        f"SELECT symbol, open, close, "
        f"ROUND(((close - open) / NULLIF(open, 0)) * 100, 2) as change_pct "
        f"FROM bronze_bhavcopy_eq "
        f"WHERE trade_date = '{latest_date}' "
        f"ORDER BY change_pct DESC LIMIT 10"
    ) if latest_date else []

    losers = query_rows(
        f"SELECT symbol, open, close, "
        f"ROUND(((close - open) / NULLIF(open, 0)) * 100, 2) as change_pct "
        f"FROM bronze_bhavcopy_eq "
        f"WHERE trade_date = '{latest_date}' "
        f"ORDER BY change_pct ASC LIMIT 10"
    ) if latest_date else []

    most_active = query_rows(
        f"SELECT symbol, close, totaltradedquantity "
        f"FROM bronze_bhavcopy_eq "
        f"WHERE trade_date = '{latest_date}' "
        f"ORDER BY totaltradedquantity DESC NULLS LAST LIMIT 10"
    ) if latest_date else []

    return {
        "trade_date": latest_date,
        "gainers": gainers,
        "losers": losers,
        "most_active": most_active,
    }


@router.get("/indices")
def market_indices() -> list[dict[str, Any]]:
    return query_rows(
        "SELECT DISTINCT index_name, symbol, company_name, weight_percentage "
        "FROM bronze_index_constituents "
        "WHERE index_name IS NOT NULL "
        "ORDER BY index_name, weight_percentage DESC"
    )


@router.get("/fo-oi")
def market_fo_oi() -> list[dict[str, Any]]:
    latest = query_rows(
        "SELECT MAX(trade_date) as trade_date FROM bronze_fo_oi"
    )
    latest_date = latest[0]["trade_date"] if latest else None
    if not latest_date:
        return []
    return query_rows(
        f"SELECT * FROM bronze_fo_oi "
        f"WHERE trade_date = '{latest_date}'"
    )


@router.get("/block-deals")
def market_block_deals(limit: int = 50) -> list[dict[str, Any]]:
    return query_rows(
        f"SELECT * FROM bronze_block_deals "
        f"ORDER BY trade_date DESC LIMIT {limit}"
    )
