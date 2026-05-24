from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class BhavcopyEqBronze(BaseModel):
    symbol: str
    series: str | None = None
    trade_date: str
    prev_close: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    last: float | None = None
    close: float | None = None
    totaltradedquantity: float | None = None
    totaltradedvalue: float | None = None
    avg_price: float | None = None
    no_of_trades: float | None = None
    deliv_qty: float | None = None
    deliv_per: float | None = None


class CorpActionsBronze(BaseModel):
    symbol: str
    ex_date: str | None = None
    purpose: str | None = None
    face_value: float | None = None
    record_date: str | None = None
    bc_start_date: str | None = None
    bc_end_date: str | None = None


class IndexConstituentsBronze(BaseModel):
    symbol: str
    company_name: str | None = None
    index_name: str | None = None
    weight_percentage: float | None = None
    industry: str | None = None
    trade_date: str


class FoOiBronze(BaseModel):
    client_type: str
    future_index_long: float | None = None
    future_index_short: float | None = None
    future_stock_long: float | None = None
    future_stock_short: float | None = None
    option_index_call_long: float | None = None
    option_index_put_long: float | None = None
    option_index_call_short: float | None = None
    option_index_put_short: float | None = None
    option_stock_call_long: float | None = None
    option_stock_put_long: float | None = None
    option_stock_call_short: float | None = None
    option_stock_put_short: float | None = None
    total_long_contracts: float | None = None
    total_short_contracts: float | None = None
    trade_date: str


class BlockDealsBronze(BaseModel):
    symbol: str
    client_name: str | None = None
    deal_type: str | None = None
    quantity: float | None = None
    price: float | None = None
    value: float | None = None
    trade_date: str


class BhavcopyEqFeatures(BaseModel):
    symbol: str
    trade_date: date
    close: float | None = None
    totaltradedquantity: float | None = None
    sma_20: float | None = None
    ema_20: float | None = None
    rsi_14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None


class FoOiFeatures(BaseModel):
    client_type: str
    net_futures: float | None = None
    net_options: float | None = None
    net_total: float | None = None
    long_short_ratio: float | None = None
    put_call_ratio: float | None = None


BRONZE_SCHEMAS: dict[str, type[BaseModel]] = {
    "bhavcopy_eq": BhavcopyEqBronze,
    "corp_actions": CorpActionsBronze,
    "index_constituents": IndexConstituentsBronze,
    "fo_oi": FoOiBronze,
    "block_deals": BlockDealsBronze,
}

GOLD_SCHEMAS: dict[str, type[BaseModel]] = {
    "bhavcopy_eq": BhavcopyEqFeatures,
    "fo_oi": FoOiFeatures,
}
