from pinaka_ingestion.s3_raw import build_raw_object_key


def test_build_raw_object_key() -> None:
    key = build_raw_object_key(dataset="bhavcopy_eq", trade_date="2026-05-22", run_id="abc123")
    assert key == "nse/bhavcopy_eq/dt=2026-05-22/run_id=abc123/part-00000.json"
