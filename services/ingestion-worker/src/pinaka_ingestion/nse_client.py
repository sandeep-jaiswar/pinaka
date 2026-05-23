from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


class NseLibError(RuntimeError):
    pass


@dataclass(frozen=True)
class PullRequest:
    dataset: str
    start_date: date
    end_date: date


def _json_safe(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, date):
        return value.isoformat()

    # pandas/numpy scalars usually expose item()
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _json_safe(item())
        except Exception:
            pass

    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}

    if isinstance(value, list):
        return [_json_safe(item_val) for item_val in value]

    return str(value)


def _rows_from_frame_like(frame_like: Any) -> list[dict]:
    if frame_like is None:
        return []

    if hasattr(frame_like, "to_dict"):
        rows = frame_like.to_dict(orient="records")
        return [_json_safe(row) for row in rows]

    if isinstance(frame_like, list):
        return [_json_safe(row) for row in frame_like]

    raise NseLibError(f"Unsupported nselib response type: {type(frame_like)!r}")


def fetch_bhavcopy_eq(trade_date: date) -> dict:
    try:
        from nselib import capital_market
    except Exception as exc:
        raise NseLibError("Failed to import nselib. Install pinaka-ingestion-worker deps.") from exc

    trade_date_ddmmyyyy = trade_date.strftime("%d-%m-%Y")

    candidate_functions: list[tuple[str, Any]] = [
        ("bhav_copy_with_delivery", getattr(capital_market, "bhav_copy_with_delivery", None)),
        ("bhav_copy_equities", getattr(capital_market, "bhav_copy_equities", None)),
    ]

    errors: list[str] = []
    for function_name, function_ref in candidate_functions:
        if not callable(function_ref):
            continue
        try:
            frame_like = function_ref(trade_date=trade_date_ddmmyyyy)
            rows = _rows_from_frame_like(frame_like)
            return {
                "dataset": "bhavcopy_eq",
                "trade_date": trade_date.isoformat(),
                "source": "nselib",
                "source_function": function_name,
                "row_count": len(rows),
                "records": rows,
            }
        except Exception as exc:
            errors.append(f"{function_name}: {exc}")

    joined = "; ".join(errors) if errors else "No compatible nselib bhavcopy function found."
    raise NseLibError(f"Unable to fetch bhavcopy equities for {trade_date.isoformat()}. {joined}")


def fetch_dataset(request: PullRequest) -> dict:
    if request.dataset == "bhavcopy_eq" and request.start_date == request.end_date:
        return fetch_bhavcopy_eq(request.start_date)

    return {
        "dataset": request.dataset,
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
        "records": [],
        "source": "nselib",
    }
