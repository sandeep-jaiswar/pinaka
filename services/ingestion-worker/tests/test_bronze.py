from __future__ import annotations

from unittest.mock import patch

import pytest

from pinaka_ingestion.pipeline.bronze import (
    _BRONZE_COLUMN_MAP,
    _normalize_field,
    _normalize_record,
    bronze_dataset_for_date,
    normalize_to_bronze,
)


class TestNormalizeField:
    def test_none(self):
        assert _normalize_field(None) is None

    def test_numbers(self):
        assert _normalize_field(42) == 42
        assert _normalize_field(3.14) == 3.14

    def test_string_stripped(self):
        assert _normalize_field("  hello  ") == "hello"

    def test_string_empty_returns_none(self):
        assert _normalize_field("") is None

    def test_string_dash_returns_none(self):
        assert _normalize_field("-") is None

    def test_other_types_passthrough(self):
        assert _normalize_field([1, 2]) == [1, 2]


class TestNormalizeRecord:
    def test_bhavcopy_eq_mapping(self):
        raw = {
            "SYMBOL": "INFY",
            "OPEN_PRICE": "1500.00",
            "HIGH_PRICE": "1520.00",
            "LOW_PRICE": "1490.00",
            "CLOSE_PRICE": "1510.00",
            "TTL_TRD_QNTY": "5000000",
            "TURNOVER_LACS": "75000.00",
        }
        result = _normalize_record("bhavcopy_eq", raw)
        assert result["symbol"] == "INFY"
        assert result["open"] == "1500.00"
        assert result["high"] == "1520.00"
        assert result["low"] == "1490.00"
        assert result["close"] == "1510.00"
        assert result["totaltradedquantity"] == "5000000"
        assert result["totaltradedvalue"] == "75000.00"

    def test_bhavcopy_eq_multiple_names(self):
        raw = {
            "symbol": "INFY",
            "open_price": "1500",
            "PREV_CLOSE": "1480",
            "prev_close": "1475",
        }
        result = _normalize_record("bhavcopy_eq", raw)
        assert result["symbol"] == "INFY"
        assert result["open"] == "1500"
        assert result["prev_close"] in ("1480", "1475")

    def test_corp_actions_mapping(self):
        raw = {"symbol": "RELIANCE", "exDate": "2026-06-01", "subject": "Dividend"}
        result = _normalize_record("corp_actions", raw)
        assert result["symbol"] == "RELIANCE"
        assert result["ex_date"] == "2026-06-01"
        assert result["purpose"] == "Dividend"

    def test_unknown_keys_are_dropped(self):
        raw = {"SYMBOL": "INFY", "UNKNOWN_COLUMN": "value"}
        result = _normalize_record("bhavcopy_eq", raw)
        assert result["symbol"] == "INFY"
        assert "unknown_column" not in result

    def test_empty_record(self):
        result = _normalize_record("bhavcopy_eq", {})
        assert result == {}

    def test_fo_oi_full_mapping(self):
        raw = {
            "Client Type": "FII",
            "Future Index Long": 1000,
            "Future Index Short": 500,
            "Option Index Call Long": 200,
            "Option Index Put Long": 300,
        }
        result = _normalize_record("fo_oi", raw)
        assert result["client_type"] == "FII"
        assert result["future_index_long"] == 1000
        assert result["future_index_short"] == 500

    def test_block_deals_mapping(self):
        raw = {
            "Symbol": "TCS",
            "ClientName": "TEST FUND",
            "Buy/Sell": "BUY",
            "QuantityTraded": 10000,
            "TradePrice/Wght.Avg.Price": 3500.50,
        }
        result = _normalize_record("block_deals", raw)
        assert result["symbol"] == "TCS"
        assert result["client_name"] == "TEST FUND"
        assert result["deal_type"] == "BUY"


class TestBronzeColumnMap:
    def test_all_datasets_have_mappings(self):
        expected = {"bhavcopy_eq", "corp_actions", "index_constituents", "fo_oi", "block_deals"}
        assert set(_BRONZE_COLUMN_MAP.keys()) == expected

    def test_bhavcopy_eq_has_all_canonical_fields(self):
        canonical = set(_BRONZE_COLUMN_MAP["bhavcopy_eq"].values())
        for field in ["symbol", "series", "trade_date", "open", "high", "low", "close"]:
            assert field in canonical


class TestNormalizeToBronze:
    @patch("pinaka_ingestion.pipeline.bronze.put_payload_parquet")
    def test_empty_records(self, mock_put):
        result = normalize_to_bronze(
            dataset="bhavcopy_eq",
            raw_records=[],
            trade_date="2026-05-22",
            run_id="test123",
        )
        assert result["row_count"] == 0
        assert result["run_id"] == "test123"
        mock_put.assert_not_called()

    @patch("pinaka_ingestion.pipeline.bronze.put_payload_parquet")
    def test_skips_none_records(self, mock_put):
        mock_put.return_value = "s3://bucket/key"
        result = normalize_to_bronze(
            dataset="bhavcopy_eq",
            raw_records=[None, {"SYMBOL": "INFY"}, None],
            trade_date="2026-05-22",
            run_id="test123",
        )
        assert result["row_count"] == 1

    @patch("pinaka_ingestion.pipeline.bronze.put_payload_parquet")
    def test_writes_parquet(self, mock_put):
        mock_put.return_value = "s3://bucket/key"
        result = normalize_to_bronze(
            dataset="bhavcopy_eq",
            raw_records=[{"SYMBOL": "INFY", "OPEN_PRICE": "1500"}],
            trade_date="2026-05-22",
            run_id="test456",
        )
        assert result["row_count"] == 1
        assert result["s3_uri"] == "s3://bucket/key"
        mock_put.assert_called_once()

    def test_carries_source_run_id(self):
        result = normalize_to_bronze(
            dataset="bhavcopy_eq",
            raw_records=[],
            trade_date="2026-05-22",
            run_id="bronze123",
            source_run_id="raw456",
        )
        assert result["source_run_id"] == "raw456"


class TestBronzeDatasetForDate:
    @patch("pinaka_ingestion.pipeline.bronze.uuid4")
    @patch("pinaka_ingestion.pipeline.bronze.put_payload_parquet")
    def test_generates_run_id(self, mock_put, mock_uuid):
        mock_uuid.return_value.hex = "generated-run-id"
        mock_put.return_value = "s3://bucket/key"
        result = bronze_dataset_for_date(
            dataset="bhavcopy_eq",
            trade_date=__import__("datetime").date(2026, 5, 22),
            raw_records=[{"SYMBOL": "TCS", "CLOSE_PRICE": "4000"}],
        )
        assert result["run_id"] == "generated-run-id"
