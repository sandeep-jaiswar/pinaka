from __future__ import annotations

import json
import math
from datetime import date
from typing import Any
from uuid import uuid4

from ..s3_raw import _s3_client, current_utc_iso, put_payload_json


def _read_bronze_records(
    *,
    dataset: str,
    trade_date: date,
    bucket: str = "pinaka-bronze",
    endpoint_url: str = "http://ministack:4566",
    region_name: str = "ap-south-1",
) -> list[dict]:
    client = _s3_client(endpoint_url=endpoint_url, region_name=region_name)
    prefix = f"nse/{dataset}/dt={trade_date.isoformat()}/"
    keys: list[str] = []
    continuation_token = None

    while True:
        if continuation_token:
            response = client.list_objects_v2(
                Bucket=bucket, Prefix=prefix, ContinuationToken=continuation_token
            )
        else:
            response = client.list_objects_v2(Bucket=bucket, Prefix=prefix)

        contents = response.get("Contents", [])
        keys.extend(item["Key"] for item in contents)
        if not response.get("IsTruncated"):
            break
        continuation_token = response.get("NextContinuationToken")

    records: list[dict] = []
    for key in keys:
        obj = client.get_object(Bucket=bucket, Key=key)
        payload = json.loads(obj["Body"].read().decode("utf-8"))
        records.extend(payload.get("records", []))

    return records


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def compute_rsi(prices: list[float], period: int = 14) -> list[float | None]:
    if len(prices) < period + 1:
        return [None] * len(prices)

    rsi_values: list[float | None] = [None] * period
    gains: list[float] = []
    losses: list[float] = []

    for i in range(1, period + 1):
        diff = prices[i] - prices[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        rsi_values.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi_values.append(100.0 - (100.0 / (1.0 + rs)))

    for i in range(period + 1, len(prices)):
        diff = prices[i] - prices[i - 1]
        gain = max(diff, 0)
        loss = max(-diff, 0)
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100.0 - (100.0 / (1.0 + rs)))

    return rsi_values


def compute_sma(prices: list[float], period: int = 20) -> list[float | None]:
    result: list[float | None] = [None] * (period - 1)
    for i in range(period - 1, len(prices)):
        result.append(sum(prices[i - period + 1 : i + 1]) / period)
    return result


def compute_ema(prices: list[float], period: int = 20) -> list[float | None]:
    if len(prices) < period:
        return [None] * len(prices)

    multiplier = 2.0 / (period + 1)
    ema_values: list[float | None] = [None] * (period - 1)
    ema = sum(prices[:period]) / period
    ema_values.append(ema)

    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
        ema_values.append(ema)

    return ema_values


def compute_macd(
    prices: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    ema_fast = compute_ema(prices, fast)
    ema_slow = compute_ema(prices, slow)

    macd_line: list[float | None] = [None] * (slow - 1)
    for i in range(slow - 1, len(prices)):
        f = ema_fast[i]
        s = ema_slow[i]
        macd_line.append(f - s if (f is not None and s is not None) else None)

    macd_values = [v for v in macd_line if v is not None]
    if not macd_values:
        return macd_line, [None] * len(prices), [None] * len(prices)

    signal_line: list[float | None] = [None] * (slow + signal - 2)
    m = compute_ema(macd_values, signal)
    signal_line[slow + signal - 2 - len(m) + 1:] = m if m else []
    while len(signal_line) < len(prices):
        signal_line.insert(0, None)

    histogram: list[float | None] = []
    for i in range(len(prices)):
        m_line = macd_line[i]
        s_line = signal_line[i]
        histogram.append(
            (m_line - s_line) if (m_line is not None and s_line is not None) else None
        )

    return macd_line, signal_line, histogram


def _compute_symbol_indicators(
    records: list[dict],
    closes: list[float],
    highs: list[float],
    lows: list[float],
    volumes: list[float],
) -> list[dict]:
    if not closes:
        return []

    sma_20 = compute_sma(closes, 20)
    ema_20 = compute_ema(closes, 20)
    rsi_14 = compute_rsi(closes, 14)
    macd_line, macd_signal, macd_hist = compute_macd(closes)

    results: list[dict] = []
    for i in range(len(records)):
        results.append({
            "symbol": records[i].get("symbol"),
            "trade_date": records[i].get("trade_date"),
            "close": closes[i],
            "volume": volumes[i] if i < len(volumes) else None,
            "sma_20": sma_20[i] if i < len(sma_20) else None,
            "ema_20": ema_20[i] if i < len(ema_20) else None,
            "rsi_14": rsi_14[i] if i < len(rsi_14) else None,
            "macd": macd_line[i] if i < len(macd_line) else None,
            "macd_signal": macd_signal[i] if i < len(macd_signal) else None,
            "macd_histogram": macd_hist[i] if i < len(macd_hist) else None,
        })
    return results


def compute_features_for_date(
    *,
    trade_date: date,
    dataset: str = "bhavcopy_eq",
    bronze_bucket: str = "pinaka-bronze",
    gold_bucket: str = "pinaka-gold",
    endpoint_url: str = "http://ministack:4566",
    region_name: str = "ap-south-1",
    lookback_days: int = 30,
) -> dict:
    all_records = _read_bronze_records(
        dataset=dataset,
        trade_date=trade_date,
        bucket=bronze_bucket,
        endpoint_url=endpoint_url,
        region_name=region_name,
    )
    if not all_records:
        return {
            "dataset": dataset,
            "trade_date": trade_date.isoformat(),
            "row_count": 0,
            "features_computed": 0,
        }

    symbols: dict[str, list[dict]] = {}
    for rec in all_records:
        sym = rec.get("symbol")
        if sym:
            symbols.setdefault(str(sym), []).append(rec)

    features: list[dict] = []
    for sym, recs in symbols.items():
        closes = [_safe_float(r.get("close")) for r in recs if _safe_float(r.get("close")) is not None]
        highs = [_safe_float(r.get("high")) for r in recs if _safe_float(r.get("high")) is not None]
        lows = [_safe_float(r.get("low")) for r in recs if _safe_float(r.get("low")) is not None]
        volumes = [_safe_float(r.get("totaltradedquantity")) for r in recs if _safe_float(r.get("totaltradedquantity")) is not None]

        if not closes:
            continue

        sym_features = _compute_symbol_indicators(recs, closes, highs, lows, volumes)
        if sym_features:
            features.append(sym_features[-1])

    run_id = uuid4().hex
    object_key = f"features/{dataset}/dt={trade_date.isoformat()}/run_id={run_id}/features.json"

    payload = {
        "dataset": dataset,
        "trade_date": trade_date.isoformat(),
        "gold_at_utc": current_utc_iso(),
        "run_id": run_id,
        "symbols": len(features),
        "records": features,
    }

    s3_uri = put_payload_json(
        bucket=gold_bucket,
        key=object_key,
        payload=payload,
        endpoint_url=endpoint_url,
        region_name=region_name,
    )

    return {
        "dataset": dataset,
        "trade_date": trade_date.isoformat(),
        "symbols": len(features),
        "bucket": gold_bucket,
        "object_key": object_key,
        "s3_uri": s3_uri,
        "run_id": run_id,
    }
