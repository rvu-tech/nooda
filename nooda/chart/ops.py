import pandas as pd
import matplotlib.ticker
import matplotlib.pyplot as plt
import numpy as np

from calendar import monthrange
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

    def data(self, raw: pd.DataFrame) -> pd.DataFrame:
        bounds = self._bounds(raw)

        return pd.concat(
            [self._series_data(raw, bounds, series) for series in self.series],
            axis=1,
        )

    def _series_data(
        self,
        df: pd.DataFrame,
        bounds: Bounds,
        series: Series,
    ) -> pd.DataFrame:
        series_df = df.copy()

        if series.offset is not None:
            series_df.index = (
                pd.to_datetime(series_df.index).to_pydatetime() + series.offset
            )

        data = (
            series_df.loc[time_window(bounds)]
            .groupby(self._clamp)[series.columns]
            .apply(series.agg)
            .dropna()
        )

        if isinstance(data, pd.DataFrame):
            data.columns = [series.label]
        elif isinstance(data, pd.Series):
            data.name = series.label

        return data

    def _plot(
        self,
        ax: plt.Axes,
        df: pd.DataFrame,
        y_formatter: Formatter,
    ):
        data = self.data(df)

        ax.xaxis.set_ticks(data.index)
        ax.xaxis.set_major_formatter(self._x_formatter())

        for series in self.series:
            ax.plot(
                data[series.label],
                label=series.label,
                **series.style._asdict(),
            )

            if series.annotations is not None:
                for point in data[series.label].items():
                    ax.annotate(
                        y_formatter.format_data(point[1]),
                        point,
                        **series.annotations._asdict(),
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
        max_dt = pd.to_datetime(df.index.max())
        latest_d = max_dt.date()

        latest_dt = datetime(
            latest_d.year, latest_d.month, latest_d.day, tzinfo=max_dt.tzinfo
        )
        earliest_dt = latest_dt - relativedelta(days=self.days)

        return Bounds(earliest=earliest_dt, latest=latest_dt)

    def _clamp(self, dt: datetime) -> datetime:
        return datetime(dt.year, dt.month, dt.day, tzinfo=dt.tzinfo)


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
        max_dt = pd.to_datetime(df.index.max())
        latest_d = max_dt.date()

        latest_dt = self._clamp(
            datetime(latest_d.year, latest_d.month, latest_d.day, tzinfo=max_dt.tzinfo)
        ) + relativedelta(weeks=1)
        earliest_dt = latest_dt - relativedelta(weeks=self.weeks)

        return Bounds(earliest=earliest_dt, latest=latest_dt)

    def _clamp(self, dt: datetime) -> datetime:
        day = datetime(dt.year, dt.month, dt.day, tzinfo=dt.tzinfo)
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
        max_dt = pd.to_datetime(df.index.max())
        latest_d = max_dt.date()

        latest_dt = datetime(
            latest_d.year, latest_d.month, 1, tzinfo=max_dt.tzinfo
        ) + relativedelta(months=1)
        earliest_dt = latest_dt - relativedelta(months=self.months)

        return Bounds(earliest=earliest_dt, latest=latest_dt)

    def _clamp(self, dt: datetime) -> datetime:
        return datetime(dt.year, dt.month, 1, tzinfo=dt.tzinfo)


class Chart:
    def __init__(
        self,
        title: Optional[str] = None,
        formatter: Formatter | str = StrMethodFormatter("{x:,.0f}"),
        plots: list[type[Plot]] = [],
        height: int = 5,
        width_increment: float = 0.5,
    ):
        assert len(plots) > 0

        if isinstance(formatter, str):
            formatter = StrMethodFormatter(formatter)

        self.title = title
        self.formatter = formatter
        self.plots = plots
        self.height = height
        self.width_increment = width_increment

    def plot(self, df):
        fig, axs = plt.subplots(
            1,
            len(self.plots),
            figsize=(
                sum(plot.increments for plot in self.plots) * self.width_increment,
                self.height,
            ),
            gridspec_kw={"width_ratios": [plot.increments for plot in self.plots]},
            sharey=True,
        )

        if self.title is not None:
            fig.suptitle(self.title)

        for pos, ax, plot in zip(range(len(self.plots)), axs, self.plots):
            plot._plot(ax, df, self.formatter)

            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            if pos > 0:
                ax.spines["left"].set_visible(False)
                plt.setp(ax.get_yticklines(), visible=False)

            ax.grid(visible=True, which="major", axis="y", alpha=0.3)
            ax.yaxis.set_major_formatter(self.formatter)
            ax.tick_params(axis="both", which="major", labelsize=9)

            for label in ax.get_xticklabels():
                label.set_fontweight(700)

            _add_legend(ax, [s.label for s in plot.series])

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.12)

        return fig

    def data(self, df):
        return [plot.data(df) for plot in self.plots]


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


def split_month_by_day(df, val_column, month_column="month", day_column="day"):
    df[day_column] = df.apply(
        lambda row: pd.date_range(
            row[month_column],
            row[month_column] + relativedelta(months=1),
            freq="D",
            inclusive="left",
        ),
        axis="columns",
    )
    df["__days_in_month"] = df.apply(
        lambda row: monthrange(row[month_column].year, row[month_column].month)[1],
        axis="columns",
    )

    df = df.explode(day_column)

    df[val_column] = df[val_column] / df["__days_in_month"]

    return df.drop(columns=[month_column, "__days_in_month"])
