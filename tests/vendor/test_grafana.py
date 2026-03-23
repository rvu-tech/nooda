from datetime import datetime, timezone

from nooda.vendor.grafana import _build_dataframe


def _make_response(values):
    """Build a minimal Prometheus query_range JSON response."""
    return {
        "data": {
            "resultType": "matrix",
            "result": [{"metric": {}, "values": values}],
        }
    }


def test_build_dataframe_truncate_aligns_timestamps():
    """Timestamps with sub-day offsets should merge into a single row per day."""
    ts1 = datetime(2025, 9, 26, 16, 40, 18, 728000, tzinfo=timezone.utc).timestamp()
    ts2 = datetime(2025, 9, 26, 16, 40, 18, 809000, tzinfo=timezone.utc).timestamp()

    results = [
        ("successful_requests", _make_response([[ts1, "100"]])),
        ("total_requests", _make_response([[ts2, "200"]])),
    ]

    df = _build_dataframe(results, truncate="1D")

    assert len(df) == 1
    assert df["successful_requests"].iloc[0] == 100.0
    assert df["total_requests"].iloc[0] == 200.0


def test_build_dataframe_without_truncate_keeps_separate_rows():
    """Without truncation, slightly different timestamps produce separate rows."""
    ts1 = datetime(2025, 9, 26, 16, 40, 18, 728000, tzinfo=timezone.utc).timestamp()
    ts2 = datetime(2025, 9, 26, 16, 40, 18, 809000, tzinfo=timezone.utc).timestamp()

    results = [
        ("successful_requests", _make_response([[ts1, "100"]])),
        ("total_requests", _make_response([[ts2, "200"]])),
    ]

    df = _build_dataframe(results)

    assert len(df) == 2
