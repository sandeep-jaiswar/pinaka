from __future__ import annotations

import json
import logging
import os
from threading import Lock
from typing import Any

from kafka import KafkaProducer

logger = logging.getLogger(__name__)


class _ProducerManager:
    def __init__(self) -> None:
        self._producer: KafkaProducer | None = None
        self._lock = Lock()
        self._brokers: str | None = None

    def get(self, brokers: str) -> KafkaProducer:
        with self._lock:
            if self._producer is None or self._brokers != brokers:
                self._close()
                self._producer = KafkaProducer(
                    bootstrap_servers=brokers,
                    value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                    acks="all",
                    retries=3,
                )
                self._brokers = brokers
            return self._producer

    def _close(self) -> None:
        if self._producer is not None:
            try:
                self._producer.close()
            except Exception:
                logger.exception("Error closing Kafka producer")

    def close(self) -> None:
        with self._lock:
            self._close()
            self._producer = None
            self._brokers = None


_producer_manager = _ProducerManager()


def _send_event(event: dict[str, Any], brokers: str, topic: str = "pinaka-ingest-jobs") -> bool:
    try:
        producer = _producer_manager.get(brokers)
        future = producer.send(topic, value=event)
        future.get(timeout=10)
        return True
    except Exception:
        logger.exception("Failed to emit event to Kafka")
        return False


def emit_ingestion_event(
    *,
    dataset: str,
    trade_date: str,
    run_id: str,
    row_count: int,
    s3_uri: str | None,
    brokers: str | None = None,
) -> bool:
    if brokers is None:
        brokers = os.getenv("PINAKA_KAFKA_BROKERS", "redpanda:9092")

    event: dict[str, Any] = {
        "event_type": "raw.ingested",
        "dataset": dataset,
        "trade_date": trade_date,
        "run_id": run_id,
        "row_count": row_count,
        "s3_uri": s3_uri,
    }
    return _send_event(event, brokers)


def emit_bronze_event(
    *,
    dataset: str,
    trade_date: str,
    run_id: str,
    source_run_id: str | None,
    row_count: int,
    s3_uri: str | None,
    brokers: str | None = None,
) -> bool:
    if brokers is None:
        brokers = os.getenv("PINAKA_KAFKA_BROKERS", "redpanda:9092")

    event: dict[str, Any] = {
        "event_type": "bronze.completed",
        "dataset": dataset,
        "trade_date": trade_date,
        "run_id": run_id,
        "source_run_id": source_run_id,
        "row_count": row_count,
        "s3_uri": s3_uri,
    }
    return _send_event(event, brokers)
