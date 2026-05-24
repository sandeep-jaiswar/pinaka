from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from pinaka_ingestion.jobs import (
    backfill_plan,
    ingest_dataset_for_date,
    ingest_dataset_range,
    normalize_raw_to_bronze_for_date,
    normalize_raw_to_bronze_range,
)


class TestBackfillPlan:
    def test_unknown_dataset(self):
        with pytest.raises(ValueError, match="Unknown dataset"):
            backfill_plan("nonexistent", date(2026, 1, 1), date(2026, 1, 10), 5)

    def test_even_chunks(self):
        plan = backfill_plan("bhavcopy_eq", date(2026, 1, 1), date(2026, 1, 10), 5)
        assert len(plan) == 2
        assert plan[0]["chunk_start"] == "2026-01-01"
        assert plan[0]["chunk_end"] == "2026-01-05"
        assert plan[1]["chunk_start"] == "2026-01-06"
        assert plan[1]["chunk_end"] == "2026-01-10"

    def test_single_day_chunks(self):
        plan = backfill_plan("fo_oi", date(2026, 6, 1), date(2026, 6, 3), 1)
        assert len(plan) == 3

    def test_single_date(self):
        plan = backfill_plan("bhavcopy_eq", date(2026, 6, 1), date(2026, 6, 1), 5)
        assert len(plan) == 1
        assert plan[0]["chunk_start"] == plan[0]["chunk_end"] == "2026-06-01"


class TestIngestDatasetForDate:
    @patch("pinaka_ingestion.jobs.list_raw_partition_keys")
    def test_skips_existing_partition(self, mock_list_keys):
        mock_list_keys.return_value = ["existing/key"]
        result = ingest_dataset_for_date(
            dataset="bhavcopy_eq",
            trade_date=date(2026, 5, 22),
            bucket="pinaka-raw",
            endpoint_url="http://localhost:4566",
            region_name="ap-south-1",
            dry_run=False,
            allow_reingest=False,
        )
        assert result["skipped"] is True
        assert result["skip_reason"] == "partition_exists"

    @patch("pinaka_ingestion.s3_raw._s3_client")
    @patch("pinaka_ingestion.jobs.list_raw_partition_keys")
    @patch("pinaka_ingestion.jobs.generate_run_id")
    def test_allow_reingest_overrides_skip(self, mock_run_id, mock_list_keys, mock_s3_client):
        mock_run_id.return_value = "test-run-id"
        mock_list_keys.return_value = ["existing/key"]

        with patch("pinaka_ingestion.jobs.EXTRACTORS") as mock_extractors:
            mock_extractors.__getitem__.return_value.return_value = {
                "row_count": 1,
                "records": [{"SYMBOL": "INFY"}],
                "source_function": "fn",
            }
            result = ingest_dataset_for_date(
                dataset="bhavcopy_eq",
                trade_date=date(2026, 5, 22),
                bucket="pinaka-raw",
                endpoint_url="http://localhost:4566",
                region_name="ap-south-1",
                dry_run=False,
                allow_reingest=True,
            )
            assert result["skipped"] is False
            assert result["row_count"] == 1

    @patch("pinaka_ingestion.jobs.list_raw_partition_keys", return_value=[])
    @patch("pinaka_ingestion.jobs.generate_run_id", return_value="test-run-id")
    def test_dry_run_does_not_write(self, mock_run_id, mock_list_keys):
        with patch("pinaka_ingestion.jobs.EXTRACTORS") as mock_extractors:
            mock_extractors.__getitem__.return_value.return_value = {
                "row_count": 2,
                "records": [{"SYMBOL": "TCS"}],
            }
            result = ingest_dataset_for_date(
                dataset="bhavcopy_eq",
                trade_date=date(2026, 5, 22),
                bucket="pinaka-raw",
                endpoint_url="http://localhost:4566",
                region_name="ap-south-1",
                dry_run=True,
                allow_reingest=False,
            )
            assert result["dry_run"] is True
            assert result["s3_uri"] is None


class TestIngestDatasetRange:
    @patch("pinaka_ingestion.jobs.ingest_dataset_for_date")
    def test_single_date_range(self, mock_ingest):
        mock_ingest.return_value = {"dataset": "bhavcopy_eq", "trade_date": "2026-05-22", "row_count": 10}
        result = ingest_dataset_range(
            dataset="bhavcopy_eq",
            start_date=date(2026, 5, 22),
            end_date=date(2026, 5, 22),
            bucket="pinaka-raw",
            endpoint_url="http://localhost:4566",
            region_name="ap-south-1",
            dry_run=False,
            allow_reingest=False,
        )
        assert result["dates_requested"] == 1
        assert result["dates_succeeded"] == 1
        assert result["rows_total"] == 10

    @patch("pinaka_ingestion.jobs.ingest_dataset_for_date")
    def test_multi_date_range(self, mock_ingest):
        mock_ingest.return_value = {"trade_date": "2026-05-22", "row_count": 5}

        result = ingest_dataset_range(
            dataset="bhavcopy_eq",
            start_date=date(2026, 5, 22),
            end_date=date(2026, 5, 24),
            bucket="pinaka-raw",
            endpoint_url="http://localhost:4566",
            region_name="ap-south-1",
            dry_run=False,
            allow_reingest=False,
        )
        assert result["dates_requested"] == 3


class TestNormalizeRawToBronze:
    @patch("pinaka_ingestion.jobs._s3_client")
    def test_skips_when_no_raw_data(self, mock_client):
        client = MagicMock()
        mock_client.return_value = client
        client.list_objects_v2.return_value = {"IsTruncated": False}

        result = normalize_raw_to_bronze_for_date(
            dataset="corp_actions",
            trade_date=date(2026, 5, 22),
            endpoint_url="http://localhost:4566",
            region_name="ap-south-1",
        )
        assert result["skipped"] is True
        assert result["skip_reason"] == "no_raw_data"

    @patch("pinaka_ingestion.pipeline.bronze.bronze_dataset_for_date")
    @patch("pinaka_ingestion.jobs._s3_client")
    def test_normalizes_when_raw_exists(self, mock_client, mock_bronze):
        mock_bronze.return_value = {"row_count": 1}

        client = MagicMock()
        mock_client.return_value = client
        client.list_objects_v2.return_value = {
            "IsTruncated": False,
            "Contents": [{"Key": "nse/corp_actions/dt=2026-05-22/run_id=x/part-00000.json"}],
        }

        body = MagicMock()
        body.read.return_value.decode.return_value = (
            '{"run_id": "raw123", "records": [{"symbol": "RELIANCE", "subject": "Dividend"}]}'
        )
        client.get_object.return_value = {"Body": body}

        result = normalize_raw_to_bronze_for_date(
            dataset="corp_actions",
            trade_date=date(2026, 5, 22),
            endpoint_url="http://localhost:4566",
            region_name="ap-south-1",
        )
        assert result["skipped"] is False
        mock_bronze.assert_called_once()
        kwargs = mock_bronze.call_args[1]
        assert kwargs["source_run_id"] == "raw123"


class TestNormalizeRawToBronzeRange:
    @patch("pinaka_ingestion.jobs.normalize_raw_to_bronze_for_date")
    def test_ranges_over_dates(self, mock_normalize):
        mock_normalize.return_value = {"row_count": 10, "trade_date": "2026-05-22"}
        result = normalize_raw_to_bronze_range(
            dataset="bhavcopy_eq",
            start_date=date(2026, 5, 22),
            end_date=date(2026, 5, 24),
            max_workers=2,
        )
        assert result["dates_requested"] == 3
