from __future__ import annotations

import pytest
from pydantic import ValidationError

from pinaka_ingestion.schemas import (
    BhavcopyEqBronze,
    BhavcopyEqFeatures,
    BlockDealsBronze,
    CorpActionsBronze,
    FoOiBronze,
    IndexConstituentsBronze,
)


class TestBhavcopyEqBronze:
    def test_valid_record(self):
        record = BhavcopyEqBronze(symbol="INFY", trade_date="2026-05-22", close=1500.0)
        assert record.symbol == "INFY"
        assert record.close == 1500.0

    def test_missing_symbol_raises(self):
        with pytest.raises(ValidationError):
            BhavcopyEqBronze(trade_date="2026-05-22")


class TestCorpActionsBronze:
    def test_valid_record(self):
        record = CorpActionsBronze(symbol="RELIANCE", ex_date="2026-06-01")
        assert record.symbol == "RELIANCE"


class TestIndexConstituentsBronze:
    def test_valid_record(self):
        record = IndexConstituentsBronze(symbol="HDFC", trade_date="2026-05-22", index_name="NIFTY 50")
        assert record.symbol == "HDFC"

    def test_missing_trade_date_raises(self):
        with pytest.raises(ValidationError):
            IndexConstituentsBronze(symbol="HDFC")


class TestFoOiBronze:
    def test_valid_record(self):
        record = FoOiBronze(client_type="FII", trade_date="2026-05-22")
        assert record.client_type == "FII"


class TestBlockDealsBronze:
    def test_valid_record(self):
        record = BlockDealsBronze(symbol="TCS", deal_type="BUY", trade_date="2026-05-22")
        assert record.deal_type == "BUY"


class TestBhavcopyEqFeatures:
    def test_valid(self):
        record = BhavcopyEqFeatures(symbol="INFY", trade_date="2026-05-22", rsi_14=65.0)
        assert record.rsi_14 == 65.0



