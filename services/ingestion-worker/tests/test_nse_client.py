from __future__ import annotations

import importlib
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from pinaka_ingestion.nse_client import (
    EXTRACTORS,
    RAW_DATASETS,
    NseLibError,
    PullRequest,
    _json_safe,
    _make_result,
    _rows_from_frame_like,
    _try_extract,
    fetch_dataset,
)

# Ensure nselib submodules are importable for patch targets
importlib.import_module("nselib.capital_market")
importlib.import_module("nselib.derivatives")
importlib.import_module("nselib.indices")


class TestJsonSafe:
    def test_none(self):
        assert _json_safe(None) is None

    def test_primitives(self):
        assert _json_safe("hello") == "hello"
        assert _json_safe(42) == 42
        assert _json_safe(3.14) == 3.14
        assert _json_safe(True) is True

    def test_date_isoformat(self):
        assert _json_safe(date(2026, 5, 22)) == "2026-05-22"

    def test_datetime_isoformat(self):
        dt = datetime(2026, 5, 22, 10, 30, 0)
        result = _json_safe(dt)
        assert isinstance(result, str)
        assert "2026-05-22" in result

    def test_dict(self):
        raw = {"key": 1, "nested": {"a": date(2026, 1, 1)}}
        result = _json_safe(raw)
        assert result == {"key": 1, "nested": {"a": "2026-01-01"}}

    def test_list(self):
        raw = [1, "two", date(2026, 1, 1)]
        result = _json_safe(raw)
        assert result == [1, "two", "2026-01-01"]

    def test_fallback_str(self):
        class Custom:
            def __str__(self):
                return "custom_str"

        result = _json_safe(Custom())
        assert result == "custom_str"


class TestRowsFromFrameLike:
    def test_none(self):
        assert _rows_from_frame_like(None) == []

    def test_dataframe_with_to_dict(self):
        mock_df = MagicMock()
        mock_df.to_dict.return_value = [{"a": 1, "b": date(2026, 1, 1)}]
        result = _rows_from_frame_like(mock_df)
        assert result == [{"a": 1, "b": "2026-01-01"}]

    def test_list_input(self):
        result = _rows_from_frame_like([{"a": 1}, {"b": date(2026, 1, 1)}])
        assert result == [{"a": 1}, {"b": "2026-01-01"}]

    def test_unsupported_type(self):
        with pytest.raises(NseLibError, match="Unsupported nselib response type"):
            _rows_from_frame_like("invalid")


class TestTryExtract:
    def test_first_success(self):
        fn1 = MagicMock(return_value=[{"col": 1}])
        fn2 = MagicMock()
        name, rows = _try_extract(date(2026, 1, 1), [("fn1", fn1), ("fn2", fn2)])
        assert name == "fn1"
        assert rows == [{"col": 1}]
        fn1.assert_called_once()
        fn2.assert_not_called()

    def test_fallback_on_failure(self):
        fn1 = MagicMock(side_effect=ValueError("first failed"))
        fn2 = MagicMock(return_value=[{"col": 2}])
        name, rows = _try_extract(date(2026, 1, 1), [("fn1", fn1), ("fn2", fn2)])
        assert name == "fn2"
        assert rows == [{"col": 2}]

    def test_all_fail(self):
        fn1 = MagicMock(side_effect=ValueError("failed"))
        fn2 = MagicMock(side_effect=RuntimeError("also failed"))
        with pytest.raises(NseLibError, match="Failed to extract for 2026-01-01"):
            _try_extract(date(2026, 1, 1), [("fn1", fn1), ("fn2", fn2)])

    def test_all_non_callable_raises(self):
        with pytest.raises(NseLibError, match="No compatible nselib function"):
            _try_extract(date(2026, 1, 1), [("not_callable", None)])


class TestMakeResult:
    def test_basic(self):
        result = _make_result("bhavcopy_eq", date(2026, 5, 22), "bhav_copy_with_delivery", [{"s": "A"}])
        assert result == {
            "dataset": "bhavcopy_eq",
            "trade_date": "2026-05-22",
            "source": "nselib",
            "source_function": "bhav_copy_with_delivery",
            "row_count": 1,
            "records": [{"s": "A"}],
        }

    def test_empty_records(self):
        result = _make_result("test_ds", date(2026, 1, 1), "fn", [])
        assert result["row_count"] == 0
        assert result["records"] == []


class TestFetchDataset:
    def test_unknown_dataset(self):
        with pytest.raises(NseLibError, match="Unknown dataset: nonexistent"):
            fetch_dataset(PullRequest("nonexistent", date(2026, 1, 1), date(2026, 1, 1)))

    def test_known_dataset_calls_extractor(self):
        mock_fn = MagicMock(return_value={"dataset": "bhavcopy_eq", "records": []})
        with patch.dict(EXTRACTORS, {"bhavcopy_eq": mock_fn}):
            result = fetch_dataset(PullRequest("bhavcopy_eq", date(2026, 1, 1), date(2026, 1, 1)))
            assert result["dataset"] == "bhavcopy_eq"
            mock_fn.assert_called_once()


class TestExtractors:
    def test_all_datasets_have_extractors(self):
        assert set(EXTRACTORS.keys()) == set(RAW_DATASETS)

    def test_extractors_are_callable(self):
        for name, fn in EXTRACTORS.items():
            assert callable(fn), f"Extractor {name} is not callable"

    def test_bhavcopy_eq_returns_expected_shape(self):
        with patch("nselib.capital_market.bhav_copy_with_delivery") as mock_fn:
            mock_fn.return_value = MagicMock()
            mock_fn.return_value.to_dict.return_value = [
                {"SYMBOL": "INFY", "OPEN_PRICE": 1500.0}
            ]
            result = EXTRACTORS["bhavcopy_eq"](date(2026, 5, 22))
            assert result["dataset"] == "bhavcopy_eq"
            assert result["row_count"] == 1

    def test_fo_oi_returns_expected_shape(self):
        with patch("nselib.derivatives.participant_wise_open_interest") as mock_fn:
            mock_fn.return_value = MagicMock()
            mock_fn.return_value.to_dict.return_value = [
                {"Client Type": "FII"}
            ]
            result = EXTRACTORS["fo_oi"](date(2026, 5, 22))
            assert result["dataset"] == "fo_oi"
            assert result["row_count"] == 1

    def test_corp_actions_returns_expected_shape(self):
        with patch("nselib.capital_market.corporate_actions_for_equity") as mock_fn:
            mock_fn.return_value = MagicMock()
            mock_fn.return_value.to_dict.return_value = [
                {"symbol": "RELIANCE", "subject": "Dividend"}
            ]
            result = EXTRACTORS["corp_actions"](date(2026, 5, 22))
            assert result["dataset"] == "corp_actions"
            assert result["row_count"] == 1
