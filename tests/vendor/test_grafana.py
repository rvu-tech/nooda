from datetime import datetime, timezone

from nooda.vendor.grafana import _build_dataframe, _build_loki_dataframe


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


def _make_loki_stream_response(streams):
    """Build a minimal Loki streams response."""
    return {"data": {"resultType": "streams", "result": streams}}


def _make_loki_matrix_response(results):
    """Build a minimal Loki matrix response."""
    return {"data": {"resultType": "matrix", "result": results}}


def test_build_loki_dataframe_streams():
    """Stream results produce a DataFrame with timestamp, line, and label columns."""
    response = _make_loki_stream_response([
        {
            "stream": {"app": "web", "env": "prod"},
            "values": [
                ["1695745218000000000", "GET /api/health 200"],
                ["1695745219000000000", "POST /api/login 401"],
            ],
        },
    ])

    df = _build_loki_dataframe(response)

    assert len(df) == 2
    assert list(df.columns) == ["timestamp", "line", "app", "env"]
    assert df["line"].iloc[0] == "GET /api/health 200"
    assert df["line"].iloc[1] == "POST /api/login 401"
    assert df["app"].iloc[0] == "web"
    assert df["env"].iloc[0] == "prod"


def test_build_loki_dataframe_matrix():
    """Matrix results produce a DataFrame with timestamp, value, and label columns."""
    ts1 = datetime(2025, 9, 26, 16, 0, 0, tzinfo=timezone.utc).timestamp()
    ts2 = datetime(2025, 9, 26, 17, 0, 0, tzinfo=timezone.utc).timestamp()

    response = _make_loki_matrix_response([
        {
            "metric": {"app": "web", "env": "prod"},
            "values": [[ts1, "42.5"], [ts2, "99.0"]],
        },
    ])

    df = _build_loki_dataframe(response)

    assert len(df) == 2
    assert list(df.columns) == ["timestamp", "value", "app", "env"]
    assert df["value"].iloc[0] == 42.5
    assert df["value"].iloc[1] == 99.0
    assert df["app"].iloc[0] == "web"


def test_build_loki_dataframe_multiple_streams():
    """Multiple streams are concatenated into a single DataFrame."""
    response = _make_loki_stream_response([
        {
            "stream": {"app": "web"},
            "values": [["1695745218000000000", "line 1"]],
        },
        {
            "stream": {"app": "api"},
            "values": [["1695745219000000000", "line 2"]],
        },
    ])

    df = _build_loki_dataframe(response)

    assert len(df) == 2
    assert df["app"].iloc[0] == "web"
    assert df["app"].iloc[1] == "api"


def test_build_loki_dataframe_empty_results():
    """Empty results return an empty DataFrame."""
    response = {"data": {"resultType": "streams", "result": []}}
    df = _build_loki_dataframe(response)
    assert df.empty


def test_build_loki_dataframe_no_data():
    """Missing data key returns an empty DataFrame."""
    df = _build_loki_dataframe({})
    assert df.empty
