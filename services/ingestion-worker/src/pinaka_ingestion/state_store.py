from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class BackfillChunk:
    start_date: date
    end_date: date


def build_chunks(start_date: date, end_date: date, chunk_days: int) -> list[BackfillChunk]:
    if chunk_days <= 0:
        raise ValueError("chunk_days must be > 0")
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")

    chunks: list[BackfillChunk] = []
    cursor = start_date

    while cursor <= end_date:
        chunk_end = min(cursor + timedelta(days=chunk_days - 1), end_date)
        chunks.append(BackfillChunk(start_date=cursor, end_date=chunk_end))
        cursor = chunk_end + timedelta(days=1)

    return chunks
