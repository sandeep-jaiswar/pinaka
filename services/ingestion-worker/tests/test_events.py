from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pinaka_ingestion.events import _producer_manager, emit_bronze_event, emit_ingestion_event


def _setup_mock_producer():
    mock_producer = MagicMock()
    mock_future = MagicMock()
    mock_producer.send.return_value = mock_future
    _producer_manager._producer = mock_producer
    _producer_manager._brokers = "localhost:9092"
    return mock_producer


class TestEmitIngestionEvent:
    def test_successful_emit(self):
        mock_producer = _setup_mock_producer()

        result = emit_ingestion_event(
            dataset="bhavcopy_eq",
            trade_date="2026-05-22",
            run_id="abc123",
            row_count=100,
            s3_uri="s3://pinaka-raw/key",
            brokers="localhost:9092",
        )
        assert result is True
        mock_producer.send.assert_called_once()
        event = mock_producer.send.call_args[1]["value"]
        assert event["event_type"] == "raw.ingested"
        assert event["dataset"] == "bhavcopy_eq"

    def test_failure_returns_false(self):
        mock_producer = _setup_mock_producer()
        mock_producer.send.side_effect = RuntimeError("Kafka unavailable")

        result = emit_ingestion_event(
            dataset="fo_oi",
            trade_date="2026-05-22",
            run_id="xyz",
            row_count=50,
            s3_uri=None,
            brokers="localhost:9092",
        )
        assert result is False


class TestEmitBronzeEvent:
    def test_successful_emit(self):
        mock_producer = _setup_mock_producer()

        result = emit_bronze_event(
            dataset="bhavcopy_eq",
            trade_date="2026-05-22",
            run_id="bronze456",
            source_run_id="raw123",
            row_count=100,
            s3_uri="s3://pinaka-bronze/key",
            brokers="localhost:9092",
        )
        assert result is True
        event = mock_producer.send.call_args[1]["value"]
        assert event["event_type"] == "bronze.completed"
        assert event["source_run_id"] == "raw123"
