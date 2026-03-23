from typing import Callable, Literal, Optional, TypeVar

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


def ratio_plot(
    numerator_column,
    denominator_column,
    label: str = "%",
    title: Optional[str] = None,
    formatter: Formatter | str = StrMethodFormatter("{x:.3%}"),
    target_column: Optional[str] = None,
    show_yoy: bool = True,
):

    ratio_columns = [numerator_column, denominator_column]
    ratio_agg = ratio(*ratio_columns)

    ratio_series = Series(
        ratio_columns,
        label=label,
        agg=ratio_agg,
        style=SeriesStyle(markersize=4),
        annotations=AnnotationStyle(),
    )

    monthly_series_to_show = []
    if show_yoy:
        ratio_yoy_series = Series(
            ratio_columns,
            label=f"{label} (YoY)",
            agg=ratio_agg,
            offset=relativedelta(months=12),
            style=SeriesStyle(markersize=4, alpha=0.4),
        )
        monthly_series_to_show = [ratio_yoy_series]

    series_to_show = [ratio_series]

    if target_column is not None:
        target_series = Series(
            target_column,
            label="Target",
            agg=max,
            style=SeriesStyle(color="green"),
        )
        series_to_show += [target_series]

    return Chart(
        title=title,
        formatter=formatter,
        plots=[
            Daily(series=series_to_show, days=7),
            Weekly(series=series_to_show, weeks=6),
            Monthly(series=series_to_show + monthly_series_to_show, months=12),
        ],
    )
