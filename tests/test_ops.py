import pytest
import pandas as pd
import numpy as np

from chartlib import ops, agg, fonts
from datetime import datetime
from dateutil.relativedelta import relativedelta


def data():
    data = pd.DataFrame(
        data={
            "day": pd.date_range(start="2021-07-01", end="2023-07-09", freq="D"),
        }
    )
    data["num_valid"] = np.random.randint(10000, 100000, data.shape[0])
    data["num_errors"] = np.random.randint(100, 1000, data.shape[0])
    data["total_num"] = data["num_valid"] + data["num_errors"]
    data["target"] = 0.9995

    data.set_index("day", inplace=True)

    return data


def test_chart():
    fonts.jakarta_sans()

    success_columns = ["num_valid", "total_num"]
    success_ratio = agg.ratio(*success_columns)

    success_series = ops.Series(
        success_columns,
        label="Success %",
        agg=success_ratio,
        style=ops.SeriesStyle(markersize=4),
        annotations=ops.AnnotationStyle(),
    )
    success_yoy_series = ops.Series(
        success_columns,
        label="Success % (YoY)",
        agg=success_ratio,
        offset=relativedelta(months=12),
        style=ops.SeriesStyle(markersize=4, alpha=0.4),
    )
    target_series = ops.Series(
        "target",
        label="Target",
        agg=max,
        style=ops.SeriesStyle(color="green"),
    )

    chart = ops.Chart(
        data(),
        title="Uswitch reliability",
        formatter="{x:.3%}",
        plots=[
            ops.Daily(series=[success_series, target_series]),
            ops.Weekly(series=[success_series, target_series]),
            ops.Monthly(
                series=[success_series, target_series, success_yoy_series],
            ),
        ],
    )

    chart.plot(data()).savefig("tests/test_chart.png")


def test_chart_no_plots():
    df = pd.DataFrame(
        data={
            "day": [1, 2, 3],
            "values": [4, 5, 6],
        }
    )

    with pytest.raises(AssertionError):
        ops.Chart(df)


def test_plot_needs_one_no_offset_series():
    with pytest.raises(AssertionError):
        ops.Plot(
            series=[
                ops.Series(
                    "values", label="Values", offset=relativedelta(days=1), agg=sum
                ),
                ops.Series(
                    "values", label="Values", offset=relativedelta(days=2), agg=sum
                ),
            ],
            increments=1,
        )


def test_monthly():
    df = data()
    monthly = ops.Monthly(
        series=[
            ops.Series("values", label="Values", agg=sum),
        ],
        months=13,
    )

    assert monthly._clamp(datetime(2023, 7, 9)) == datetime(2023, 7, 1)

    bounds = monthly._bounds(df)

    assert bounds.earliest == datetime(2022, 7, 1)
    assert bounds.latest == datetime(2023, 8, 1)


def test_weekly():
    df = data()
    weekly = ops.Weekly(
        series=[
            ops.Series("values", label="Values", agg=sum),
        ],
        weeks=3,
    )

    assert weekly._clamp(datetime(2023, 7, 9)) == datetime(2023, 7, 3)

    bounds = weekly._bounds(df)

    assert bounds.earliest == datetime(2023, 6, 19)
    assert bounds.latest == datetime(2023, 7, 10)


def test_daily():
    df = data()
    daily = ops.Daily(
        series=[
            ops.Series("values", label="Values", agg=sum),
        ],
        days=13,
    )

    assert daily._clamp(datetime(2023, 7, 9, 12)) == datetime(2023, 7, 9, 0)

    bounds = daily._bounds(df)

    assert bounds.earliest == datetime(2023, 6, 26)
    assert bounds.latest == datetime(2023, 7, 9)


def test_monthly_series_df():
    success_columns = ["num_valid", "total_num"]
    success_ratio = agg.ratio(*success_columns)

    series = ops.Series(success_columns, label="Values", agg=success_ratio)
    offset_series = ops.Series(
        success_columns,
        label="Values",
        agg=success_ratio,
        offset=relativedelta(years=1),
    )

    monthly = ops.Monthly(
        series=[
            series,
            offset_series,
        ]
    )

    df = data()
    series_df = monthly._series_data(df, monthly._bounds(df), series)
    offset_df = monthly._series_data(df, monthly._bounds(df), offset_series)

    assert series_df.index.max() == offset_df.index.max()
