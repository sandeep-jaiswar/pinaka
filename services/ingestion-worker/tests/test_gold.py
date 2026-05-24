from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from pinaka_ingestion.pipeline.gold import (
    _collect_bronze_range,
    _download_s3_parquet,
    compute_features_for_date,
    compute_fo_oi_features_for_date,
)


class TestDownloadS3Parquet:
    @patch("pinaka_ingestion.pipeline.gold.pl.read_parquet")
    def test_downloads_and_reads(self, mock_read):
        mock_read.return_value.to_dicts.return_value = [{"symbol": "INFY", "close": 1500.0}]
        client = MagicMock()
        body = MagicMock()
        body.read.return_value = b"parquet_bytes"
        client.get_object.return_value = {"Body": body}

        result = _download_s3_parquet(client, "bucket", "key")
        assert result == [{"symbol": "INFY", "close": 1500.0}]
        client.get_object.assert_called_with(Bucket="bucket", Key="key")
        mock_read.assert_called_once()


class TestCollectBronzeRange:
    @patch("pinaka_ingestion.pipeline.gold.list_all_keys")
    @patch("pinaka_ingestion.pipeline.gold._download_s3_parquet")
    @patch("pinaka_ingestion.pipeline.gold._s3_client")
    def test_collects_parquet(self, mock_s3_client, mock_download, mock_list_keys):
        mock_list_keys.return_value = ["nse/bhavcopy_eq/dt=2026-05-22/run_id=x/part-00000.parquet"]
        mock_download.return_value = [{"symbol": "INFY", "close": 1500.0}]
        client = MagicMock()
        mock_s3_client.return_value = client

        result = _collect_bronze_range(
            dataset="bhavcopy_eq",
            start_date=date(2026, 5, 22),
            end_date=date(2026, 5, 22),
            bucket="pinaka-bronze",
            endpoint_url="http://localhost:4566",
            region_name="ap-south-1",
        )
        assert len(result) == 1
        assert result[0]["symbol"] == "INFY"
        assert result[0]["trade_date"] == "2026-05-22"


class TestComputeFeaturesForDate:
    def test_empty_raw_returns_empty(self):
        with patch("pinaka_ingestion.pipeline.gold._collect_bronze_range", return_value=[]):
            result = compute_features_for_date(
                trade_date=date(2026, 5, 22),
                lookback_days=30,
            )
            assert result["symbols"] == 0

    def test_missing_columns_returns_empty(self):
        with patch("pinaka_ingestion.pipeline.gold._collect_bronze_range", return_value=[{"symbol": "INFY"}]):
            result = compute_features_for_date(
                trade_date=date(2026, 5, 22),
                lookback_days=30,
            )
            assert result["symbols"] == 0

    @patch("pinaka_ingestion.pipeline.gold.put_payload_parquet")
    def test_computes_sma_ema_rsi_macd(self, mock_put):
        mock_put.return_value = "s3://pinaka-gold/features.parquet"

        target_date = date(2026, 5, 22)
        raw = []
        for i in range(30):
            d = target_date - timedelta(days=29 - i)
            raw.append({
                "symbol": "INFY",
                "trade_date": d.isoformat(),
                "close": 1500.0 + i * 10,
                "high": 1520.0 + i * 10,
                "low": 1480.0 + i * 10,
                "totaltradedquantity": 1000000,
                "open": 1490.0 + i * 10,
            })

        with patch("pinaka_ingestion.pipeline.gold._collect_bronze_range", return_value=raw):
            result = compute_features_for_date(
                trade_date=target_date,
                dataset="bhavcopy_eq",
                lookback_days=30,
            )
            assert result["symbols"] > 0
            assert result["dataset"] == "bhavcopy_eq"
            mock_put.assert_called_once()


class TestComputeFoOiFeatures:
    def test_empty_raw_returns_empty(self):
        with patch("pinaka_ingestion.pipeline.gold._collect_bronze_range", return_value=[]):
            result = compute_fo_oi_features_for_date(
                trade_date=date(2026, 5, 22),
            )
            assert result["records"] == 0

    def test_missing_columns_returns_empty(self):
        with patch("pinaka_ingestion.pipeline.gold._collect_bronze_range", return_value=[{"client_type": "FII"}]):
            result = compute_fo_oi_features_for_date(
                trade_date=date(2026, 5, 22),
            )
            assert result["records"] == 0

    @patch("pinaka_ingestion.pipeline.gold.put_payload_parquet")
    def test_computes_oi_metrics(self, mock_put):
        mock_put.return_value = "s3://pinaka-gold/features.parquet"

        raw = [{
            "client_type": "FII",
            "future_index_long": 1000.0,
            "future_index_short": 500.0,
            "future_stock_long": 200.0,
            "future_stock_short": 100.0,
            "option_index_call_long": 300.0,
            "option_index_put_long": 150.0,
            "option_index_call_short": 100.0,
            "option_index_put_short": 50.0,
            "option_stock_call_long": 100.0,
            "option_stock_put_long": 50.0,
            "option_stock_call_short": 50.0,
            "option_stock_put_short": 25.0,
            "total_long_contracts": 2000.0,
            "total_short_contracts": 1000.0,
            "trade_date": "2026-05-22",
        }]

        with patch("pinaka_ingestion.pipeline.gold._collect_bronze_range", return_value=raw):
            result = compute_fo_oi_features_for_date(
                trade_date=date(2026, 5, 22),
            )
            assert result["records"] > 0
            mock_put.assert_called_once()
