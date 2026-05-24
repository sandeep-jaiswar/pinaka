from __future__ import annotations

from unittest.mock import MagicMock, patch

from pinaka_common.cloud import list_all_keys
from pinaka_ingestion.s3_raw import (
    build_raw_object_key,
    generate_run_id,
    put_payload_json,
    put_payload_parquet,
)


class TestBuildRawObjectKey:
    def test_basic(self):
        key = build_raw_object_key(dataset="bhavcopy_eq", trade_date="2026-05-22", run_id="abc123")
        assert key == "nse/bhavcopy_eq/dt=2026-05-22/run_id=abc123/part-00000.json"

    def test_different_dataset(self):
        key = build_raw_object_key(dataset="fo_oi", trade_date="2026-06-01", run_id="xyz789")
        assert key == "nse/fo_oi/dt=2026-06-01/run_id=xyz789/part-00000.json"

    def test_run_id_included(self):
        key = build_raw_object_key(dataset="index_constituents", trade_date="2026-03-15", run_id="my-run-001")
        assert "run_id=my-run-001" in key


class TestGenerateRunId:
    def test_returns_hex_string(self):
        rid = generate_run_id()
        assert isinstance(rid, str)
        assert len(rid) == 32
        int(rid, 16)

    def test_unique(self):
        ids = {generate_run_id() for _ in range(100)}
        assert len(ids) == 100


class TestPutPayloadJson:
    @patch("pinaka_ingestion.s3_raw._s3_client")
    def test_puts_json(self, mock_client_factory):
        client = MagicMock()
        mock_client_factory.return_value = client

        uri = put_payload_json(
            bucket="pinaka-raw",
            key="test/key.json",
            payload={"records": [{"a": 1}]},
            endpoint_url="http://localhost:4566",
            region_name="ap-south-1",
        )
        assert uri == "s3://pinaka-raw/test/key.json"
        client.put_object.assert_called_once()
        call_kwargs = client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "pinaka-raw"
        assert call_kwargs["Key"] == "test/key.json"
        assert call_kwargs["ContentType"] == "application/json"


class TestPutPayloadParquet:
    @patch("pinaka_ingestion.s3_raw._s3_client")
    def test_puts_parquet(self, mock_client_factory):
        import polars as pl

        client = MagicMock()
        mock_client_factory.return_value = client
        df = pl.DataFrame({"symbol": ["INFY"], "close": [1500.0]})

        uri = put_payload_parquet(
            bucket="pinaka-bronze",
            key="test/key.parquet",
            df=df,
            endpoint_url="http://localhost:4566",
            region_name="ap-south-1",
        )
        assert uri == "s3://pinaka-bronze/test/key.parquet"
        client.put_object.assert_called_once()
        call_kwargs = client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "pinaka-bronze"
        assert call_kwargs["ContentType"] == "application/octet-stream"


class TestListAllKeys:
    def test_no_results(self):
        client = MagicMock()
        client.list_objects_v2.return_value = {"IsTruncated": False}
        keys = list_all_keys(client, "bucket", "prefix/")
        assert keys == []

    def test_single_page(self):
        client = MagicMock()
        client.list_objects_v2.return_value = {
            "IsTruncated": False,
            "Contents": [{"Key": "prefix/a.json"}, {"Key": "prefix/b.json"}],
        }
        keys = list_all_keys(client, "bucket", "prefix/")
        assert keys == ["prefix/a.json", "prefix/b.json"]

    def test_pagination(self):
        client = MagicMock()
        client.list_objects_v2.side_effect = [
            {
                "IsTruncated": True,
                "NextContinuationToken": "token1",
                "Contents": [{"Key": "prefix/a.json"}],
            },
            {
                "IsTruncated": False,
                "Contents": [{"Key": "prefix/b.json"}],
            },
        ]
        keys = list_all_keys(client, "bucket", "prefix/")
        assert keys == ["prefix/a.json", "prefix/b.json"]
        assert client.list_objects_v2.call_count == 2

    def test_pagination_without_next_token(self):
        client = MagicMock()
        client.list_objects_v2.side_effect = [
            {
                "IsTruncated": True,
                "NextContinuationToken": None,
                "Contents": [{"Key": "prefix/a.json"}],
            },
            {
                "IsTruncated": False,
                "Contents": [{"Key": "prefix/b.json"}],
            },
        ]
        keys = list_all_keys(client, "bucket", "prefix/")
        assert keys == ["prefix/a.json", "prefix/b.json"]
