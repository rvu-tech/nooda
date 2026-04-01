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
    formatter: Formatter | str = None,
    y_limits: Optional[tuple[float, float]] = None,
    agg: Callable[[list[T]], T] = np.sum,
    views: Optional[list[str]] = None,
    height: int = 5,
    width_increment: float = 0.7,
    show_legend: bool = True,
):
    return Chart(
        title=title,
        formatter=formatter,
        y_limits=y_limits,
        agg=agg,
        views=views,
        height=height,
        width_increment=width_increment,
        show_legend=show_legend,
    ).plot(df)


VIEWS_MAP = {
    "daily": lambda series, daily_series=None, **_: Daily(
        series=series + (daily_series or []), days=7
    ),
    "weekly": lambda series, **_: Weekly(series=series, weeks=6),
    "monthly": lambda series, monthly_series=None, **_: Monthly(
        series=series + (monthly_series or []), months=12
    ),
}


def ratio_plot(
    numerator_column,
    denominator_column,
    label: str = "%",
    title: Optional[str] = None,
    formatter: Formatter | str = StrMethodFormatter("{x:.3%}"),
    target_column: Optional[str] = None,
    show_yoy: bool = True,
    show_wow: bool = True,
    views: Optional[list[str]] = None,
    height: int = 5,
    width_increment: float = 0.7,
    show_legend: bool = True,
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

    daily_series_to_show = []
    if show_wow:
        ratio_wow_series = Series(
            ratio_columns,
            label=f"{label} (WoW)",
            agg=ratio_agg,
            offset=relativedelta(days=7),
            style=SeriesStyle(markersize=4, alpha=0.4),
        )
        daily_series_to_show = [ratio_wow_series]

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
            agg=np.max,
            style=SeriesStyle(color="green"),
        )
        series_to_show += [target_series]

    selected_views = views if views is not None else ["daily", "weekly", "monthly"]

    plots = []
    for view in selected_views:
        if view not in VIEWS_MAP:
            raise ValueError(
                f"Unknown view '{view}'. Valid views: {sorted(VIEWS_MAP.keys())}"
            )
        plots.append(
            VIEWS_MAP[view](
                series=series_to_show,
                daily_series=daily_series_to_show,
                monthly_series=monthly_series_to_show,
            )
        )

    return Chart(
        title=title,
        formatter=formatter,
        plots=plots,
        height=height,
        width_increment=width_increment,
        show_legend=show_legend,
    )
