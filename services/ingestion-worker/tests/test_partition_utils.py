from datetime import date

import pytest

from pinaka_ingestion.state_store import build_chunks


class TestBuildChunks:
    def test_even_windows(self):
        chunks = build_chunks(date(2026, 1, 1), date(2026, 1, 10), 5)
        assert len(chunks) == 2
        assert chunks[0].start_date.isoformat() == "2026-01-01"
        assert chunks[0].end_date.isoformat() == "2026-01-05"
        assert chunks[1].start_date.isoformat() == "2026-01-06"
        assert chunks[1].end_date.isoformat() == "2026-01-10"

    def test_single_day_chunks(self):
        chunks = build_chunks(date(2026, 6, 1), date(2026, 6, 3), 1)
        assert len(chunks) == 3
        assert chunks[0].start_date == chunks[0].end_date == date(2026, 6, 1)
        assert chunks[1].start_date == chunks[1].end_date == date(2026, 6, 2)
        assert chunks[2].start_date == chunks[2].end_date == date(2026, 6, 3)

    def test_single_date(self):
        chunks = build_chunks(date(2026, 6, 1), date(2026, 6, 1), 10)
        assert len(chunks) == 1
        assert chunks[0].start_date == chunks[0].end_date == date(2026, 6, 1)

    def test_chunk_size_larger_than_range(self):
        chunks = build_chunks(date(2026, 1, 1), date(2026, 1, 5), 100)
        assert len(chunks) == 1
        assert chunks[0].start_date == date(2026, 1, 1)
        assert chunks[0].end_date == date(2026, 1, 5)

    def test_zero_chunk_days_raises(self):
        with pytest.raises(ValueError, match="chunk_days must be > 0"):
            build_chunks(date(2026, 1, 1), date(2026, 1, 10), 0)

    def test_negative_chunk_days_raises(self):
        with pytest.raises(ValueError, match="chunk_days must be > 0"):
            build_chunks(date(2026, 1, 1), date(2026, 1, 10), -1)

    def test_end_before_start_raises(self):
        with pytest.raises(ValueError, match="end_date must be on or after start_date"):
            build_chunks(date(2026, 2, 1), date(2026, 1, 1), 5)

    def test_same_start_and_end(self):
        chunks = build_chunks(date(2026, 6, 15), date(2026, 6, 15), 7)
        assert len(chunks) == 1
        assert chunks[0].start_date == chunks[0].end_date == date(2026, 6, 15)
