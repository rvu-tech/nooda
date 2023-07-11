import pandas as pd
import matplotlib.ticker
import matplotlib.pyplot as plt
import numpy as np

from collections import namedtuple
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from pandas.core.groupby import DataFrameGroupBy
from matplotlib.dates import num2date
from matplotlib.ticker import Formatter, StrMethodFormatter, FuncFormatter
from typing import Optional, Callable, TypeVar


T = TypeVar("T")

SeriesStyle = namedtuple(
    "SeriesStyle",
    field_names=["color", "alpha", "linestyle", "marker", "markersize"],
    defaults=["black", 1.0, "-", "o", 0],
)

AnnotationStyle = namedtuple(
    "AnnotationStyle",
    field_names=["textcoords", "xytext", "ha", "fontsize"],
    defaults=["offset points", (0, 10), "center", 8],
)

Bounds = namedtuple("Bounds", ["earliest", "latest"])


class Series:
    def __init__(
        self,
        columns: list[str] | str,
        label: str,
        agg: Callable[[list[T]], T],
        offset: Optional[relativedelta] = None,
        style: SeriesStyle = SeriesStyle(),
        annotations: Optional[AnnotationStyle] = None,
    ):
        if isinstance(columns, list):
            self.columns = columns
        else:
            self.columns = [columns]

        self.label = label
        self.agg = agg
        self.offset = offset
        self.style = style
        self.annotations = annotations


def time_window(bounds):
    def fn(row):
        dt = pd.to_datetime(row.index).to_pydatetime()
        return np.logical_and(dt >= bounds.earliest, dt < bounds.latest)

    return fn


class Plot:
    def __init__(
        self,
        series: list[Series],
        increments: int,
    ):
        assert len([s for s in series if s.offset is None]) > 0

        self.series = series
        self.increments = increments

    def _plot(
        self,
        ax: plt.Axes,
        df: pd.DataFrame,
        y_formatter: Formatter,
    ):
        bounds = self._bounds(df)

        ax.xaxis.set_major_formatter(self._x_formatter())

        for series in self.series:
            series_df = self._series_df(df, bounds, series)

            if series.offset is None:
                ax.xaxis.set_ticks(series_df.index)

            ax.plot(
                series_df,
                label=series.label,
                **series.style._asdict(),
            )

            if series.annotations is not None:
                for point in series_df.items():
                    ax.annotate(
                        y_formatter.format_data(point[1]),
                        point,
                        **series.annotations._asdict(),
                    )

    def _series_df(
        self,
        df: pd.DataFrame,
        bounds: Bounds,
        series: Series,
    ) -> pd.DataFrame:
        series_df = df.copy()

        if series.offset is not None:
            series_df.index = pd.to_datetime(series_df.index).date + series.offset

        return (
            series_df.loc[time_window(bounds)]
            .groupby(self._clamp)[series.columns]
            .apply(series.agg)
        )

    def _x_formatter(self) -> Formatter:
        raise NotImplementedError()

    def _bounds(self, df: pd.DataFrame) -> Bounds:
        raise NotImplementedError()

    def _clamp(self, dt: datetime) -> datetime:
        raise NotImplementedError()


class Daily(Plot):
    def __init__(
        self,
        series: list[Series],
        days: int = 7,
    ):
        super().__init__(series=series, increments=days)

        self.days = days

    def _x_formatter(self) -> Formatter:
        return FuncFormatter(lambda d, _: num2date(d).strftime("%m/%d"))

    def _bounds(self, df: pd.DataFrame) -> datetime:
        latest_d = pd.to_datetime(df.index.max()).date()

        latest_dt = datetime(latest_d.year, latest_d.month, latest_d.day)
        earliest_dt = latest_dt - relativedelta(days=self.days)

        return Bounds(earliest=earliest_dt, latest=latest_dt)

    def _clamp(self, dt: datetime) -> datetime:
        return datetime(dt.year, dt.month, dt.day)


class Weekly(Plot):
    def __init__(
        self,
        series: list[Series],
        weeks: int = 6,
    ):
        super().__init__(series=series, increments=weeks)

        self.weeks = weeks

    def _x_formatter(self) -> Formatter:
        return FuncFormatter(lambda d, _: num2date(d).strftime("Wk\n%m/%d"))

    def _bounds(self, df: pd.DataFrame) -> datetime:
        latest_d = pd.to_datetime(df.index.max()).date()

        latest_dt = self._clamp(
            datetime(latest_d.year, latest_d.month, latest_d.day)
        ) + relativedelta(weeks=1)
        earliest_dt = latest_dt - relativedelta(weeks=self.weeks)

        return Bounds(earliest=earliest_dt, latest=latest_dt)

    def _clamp(self, dt: datetime) -> datetime:
        day = datetime(dt.year, dt.month, dt.day)
        return day - relativedelta(days=day.weekday())


class Monthly(Plot):
    def __init__(
        self,
        series: list[Series],
        months: int = 12,
    ):
        super().__init__(series=series, increments=months)

        self.months = months

    def _x_formatter(self) -> Formatter:
        return FuncFormatter(lambda d, _: num2date(d).strftime("%b"))

    def _bounds(self, df: pd.DataFrame) -> datetime:
        latest_d = pd.to_datetime(df.index.max()).date()

        latest_dt = datetime(latest_d.year, latest_d.month, 1) + relativedelta(months=1)
        earliest_dt = latest_dt - relativedelta(months=self.months)

        return Bounds(earliest=earliest_dt, latest=latest_dt)

    def _clamp(self, dt: datetime) -> datetime:
        return datetime(dt.year, dt.month, 1)


def Chart(
    df: pd.DataFrame,
    title: Optional[str] = None,
    formatter: Formatter | str = StrMethodFormatter("{x:,.0f}"),
    plots: list[type[Plot]] = [],
):
    num_plots = len(plots)

    assert num_plots > 0

    if isinstance(formatter, str):
        formatter = StrMethodFormatter(formatter)

    fig, axs = plt.subplots(
        1,
        num_plots,
        figsize=(sum(plot.increments for plot in plots) * 0.8, 5),
        gridspec_kw={"width_ratios": [plot.increments for plot in plots]},
        sharey=True,
    )

    if title is not None:
        fig.suptitle(title)

    for pos, ax, plot in zip(range(num_plots), axs, plots):
        plot._plot(ax, df, formatter)

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        if pos > 0:
            ax.spines["left"].set_visible(False)
            plt.setp(ax.get_yticklines(), visible=False)

        ax.grid(visible=True, which="major", axis="y", alpha=0.3)
        ax.yaxis.set_major_formatter(formatter)
        ax.tick_params(axis="both", which="major", labelsize=9)

        for label in ax.get_xticklabels():
            label.set_fontweight(700)

        _add_legend(ax, [s.label for s in plot.series])

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.12)

    return fig


def _add_legend(ax, labels):
    box = ax.get_position()
    ax.set_position([box.x0, box.y0 + box.height * 0.1, box.width, box.height * 0.9])

    # Put a legend below current axis
    ax.legend(
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.07),
        fancybox=False,
        shadow=False,
        ncol=len(labels),
        frameon=False,
        fontsize=8,
    )
