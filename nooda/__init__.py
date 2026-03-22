from typing import Callable, Optional, TypeVar

import numpy as np
from matplotlib.ticker import Formatter, StrMethodFormatter

from .chart.ops import Chart, Plot


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
