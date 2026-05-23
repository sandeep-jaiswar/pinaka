from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable


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


def _try_extract(
    trade_date: date,
    candidates: list[tuple[str, Callable[[str], Any]]],
) -> tuple[str, list[dict]]:
    trade_date_ddmmyyyy = trade_date.strftime("%d-%m-%Y")
    errors: list[str] = []
    for function_name, function_ref in candidates:
        if not callable(function_ref):
            continue
        try:
            frame_like = function_ref(trade_date=trade_date_ddmmyyyy)
            rows = _rows_from_frame_like(frame_like)
            return function_name, rows
        except Exception as exc:
            errors.append(f"{function_name}: {exc}")

    joined = "; ".join(errors) if errors else "No compatible nselib function found."
    raise NseLibError(f"Failed to extract for {trade_date.isoformat()}. {joined}")


def _make_result(
    dataset: str,
    trade_date: date,
    source_function: str,
    records: list[dict],
) -> dict:
    return {
        "dataset": dataset,
        "trade_date": trade_date.isoformat(),
        "source": "nselib",
        "source_function": source_function,
        "row_count": len(records),
        "records": records,
    }


def fetch_bhavcopy_eq(trade_date: date) -> dict:
    from nselib import capital_market

    fn_name, rows = _try_extract(trade_date, [
        ("bhav_copy_with_delivery", getattr(capital_market, "bhav_copy_with_delivery", None)),
        ("bhav_copy_equities", getattr(capital_market, "bhav_copy_equities", None)),
    ])
    return _make_result("bhavcopy_eq", trade_date, fn_name, rows)


def fetch_corp_actions(trade_date: date) -> dict:
    from datetime import timedelta
    from nselib import capital_market

    trade_date_ddmmyyyy = trade_date.strftime("%d-%m-%Y")
    next_date_ddmmyyyy = (trade_date + timedelta(days=1)).strftime("%d-%m-%Y")
    fn = getattr(capital_market, "corporate_actions_for_equity", None)
    if fn:
        frame_like = fn(from_date=trade_date_ddmmyyyy, to_date=next_date_ddmmyyyy)
        rows = _rows_from_frame_like(frame_like)
        return _make_result("corp_actions", trade_date, "corporate_actions_for_equity", rows)

    raise NseLibError(
        f"Failed to extract for {trade_date.isoformat()}. "
        "corporate_actions_for_equity: function not found in nselib.capital_market"
    )


def fetch_index_constituents(trade_date: date) -> dict:
    from nselib import indices

    rows: list[dict] = []
    for index_name in ["NIFTY 50", "NIFTY NEXT 50", "NIFTY MIDCAP 150", "NIFTY SMALLCAP 250"]:
        try:
            frame_like = indices.constituent_stock_list(index_symbol=index_name)
            index_rows = _rows_from_frame_like(frame_like)
            for r in index_rows:
                r["index_name"] = index_name
            rows.extend(index_rows)
        except Exception:
            pass

    return _make_result("index_constituents", trade_date, "constituent_stock_list", rows)


def fetch_fo_oi(trade_date: date) -> dict:
    from nselib import derivatives

    fn_name, rows = _try_extract(trade_date, [
        ("participant_wise_open_interest", getattr(derivatives, "participant_wise_open_interest", None)),
    ])
    return _make_result("fo_oi", trade_date, fn_name, rows)


def fetch_block_deals(trade_date: date) -> dict:
    from datetime import timedelta
    from nselib import capital_market

    trade_date_ddmmyyyy = trade_date.strftime("%d-%m-%Y")
    next_date_ddmmyyyy = (trade_date + timedelta(days=1)).strftime("%d-%m-%Y")
    fn = getattr(capital_market, "block_deals_data", None)
    if fn:
        frame_like = fn(from_date=trade_date_ddmmyyyy, to_date=next_date_ddmmyyyy)
        rows = _rows_from_frame_like(frame_like)
        return _make_result("block_deals", trade_date, "block_deals_data", rows)

    raise NseLibError(
        f"Failed to extract for {trade_date.isoformat()}. "
        "block_deals_data: function not found in nselib.capital_market"
    )


EXTRACTORS: dict[str, Callable[[date], dict]] = {
    "bhavcopy_eq": fetch_bhavcopy_eq,
    "corp_actions": fetch_corp_actions,
    "index_constituents": fetch_index_constituents,
    "fo_oi": fetch_fo_oi,
    "block_deals": fetch_block_deals,
}

RAW_DATASETS: list[str] = list(EXTRACTORS.keys())


def fetch_dataset(request: PullRequest) -> dict:
    extractor = EXTRACTORS.get(request.dataset)
    if extractor is None:
        raise NseLibError(f"Unknown dataset: {request.dataset}. Available: {list(EXTRACTORS)}")

    result = extractor(request.start_date)
    return result
