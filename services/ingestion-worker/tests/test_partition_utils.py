from datetime import date

from pinaka_ingestion.state_store import build_chunks


def test_build_chunks_even_windows() -> None:
    chunks = build_chunks(date(2026, 1, 1), date(2026, 1, 10), 5)
    assert len(chunks) == 2
    assert chunks[0].start_date.isoformat() == "2026-01-01"
    assert chunks[0].end_date.isoformat() == "2026-01-05"
    assert chunks[1].start_date.isoformat() == "2026-01-06"
    assert chunks[1].end_date.isoformat() == "2026-01-10"
