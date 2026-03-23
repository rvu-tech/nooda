from typing import Callable, Optional, TypeVar

import numpy as np
from dateutil.relativedelta import relativedelta
from matplotlib.ticker import Formatter, StrMethodFormatter

from .chart.agg import ratio
from .chart.ops import (
    AnnotationStyle,
    Chart,
    Daily,
    Monthly,
    Series,
    SeriesStyle,
    Weekly,
)


def FinancialFormatter(symbol="$", dp=0):
    return symbol + "{x:,." + str(dp) + "f}"


T = TypeVar("T")


def plot(
    df,
    *,
    title: Optional[str] = None,
    formatter: Formatter | str = StrMethodFormatter("{x:,.0f}"),
    y_limits: Optional[tuple[float, float]] = None,
    agg: Callable[[list[T]], T] = np.sum,
):
    return Chart(title=title, formatter=formatter, y_limits=y_limits, agg=agg).plot(df)


def reliability(
    df,
    success_column,
    total_column,
    title: Optional[str] = None,
    target_column: Optional[str] = None,
):

    success_columns = [success_column, total_column]
    success_ratio = ratio(*success_columns)

    success_series = Series(
        success_columns,
        label="Success %",
        agg=success_ratio,
        style=SeriesStyle(markersize=4),
        annotations=AnnotationStyle(),
    )

    days_in_index = (df.index.max() - df.index.min()).days
    monthly_series_to_show = []
    if days_in_index > 365:
        success_yoy_series = Series(
            success_columns,
            label="Success % (YoY)",
            agg=success_ratio,
            offset=relativedelta(months=12),
            style=SeriesStyle(markersize=4, alpha=0.4),
        )
        monthly_series_to_show = [success_yoy_series]

    series_to_show = [success_series]

    if target_column is not None:
        target_series = Series(
            target_column,
            label="Target",
            agg=max,
            style=SeriesStyle(color="green"),
        )
        series_to_show += [target_series]

    chart = Chart(
        title=title,
        formatter="{x:.3%}",
        plots=[
            Daily(series=series_to_show, days=7),
            Weekly(series=series_to_show, weeks=6),
            Monthly(series=series_to_show + monthly_series_to_show, months=12),
        ],
    )

    return chart.plot(df)
