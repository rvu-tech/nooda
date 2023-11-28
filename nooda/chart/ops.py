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
        range_columns: Optional[list[str]] = None,
    ):
        assert len([s for s in series if s.offset is None]) > 0

        self.series = series
        self.increments = increments
        self.range_columns = range_columns

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
                        y_formatter.format_data(point[1])
                        if y_formatter is not None
                        else point[1],
                        point,
                        **series.annotations._asdict(),
                    )

    def _max_dt(self, df: pd.DataFrame):
        if self.range_columns is not None:
            series_columns = self.range_columns
        else:
            series_columns = [col for s in self.series for col in s.columns]
        return pd.to_datetime(df[df[series_columns].notnull().any(axis=1)].index.max())

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
        range_columns: Optional[list[str]] = None,
    ):
        super().__init__(series=series, increments=days, range_columns=range_columns)

        self.days = days

    def _x_formatter(self) -> Formatter:
        return FuncFormatter(lambda d, _: num2date(d).strftime("%m/%d"))

    def _bounds(self, df: pd.DataFrame) -> datetime:
        max_dt = self._max_dt(df)
        latest_d = max_dt.date()

        latest_dt = datetime(
            latest_d.year, latest_d.month, latest_d.day, tzinfo=max_dt.tzinfo
        )
        earliest_dt = latest_dt - relativedelta(days=self.days)

        return Bounds(earliest=earliest_dt, latest=latest_dt)

    def _clamp(self, dt: datetime) -> datetime:
        tzinfo = dt.tzinfo if "tzinfo" in dir(dt) else None
        return datetime(dt.year, dt.month, dt.day, tzinfo=tzinfo)


class Weekly(Plot):
    def __init__(
        self,
        series: list[Series],
        weeks: int = 6,
        range_columns: Optional[list[str]] = None,
    ):
        super().__init__(series=series, increments=weeks, range_columns=range_columns)

        self.weeks = weeks

    def _x_formatter(self) -> Formatter:
        return FuncFormatter(lambda d, _: num2date(d).strftime("Wk\n%m/%d"))

    def _bounds(self, df: pd.DataFrame) -> datetime:
        max_dt = self._max_dt(df)
        latest_d = max_dt.date()

        latest_dt = self._clamp(
            datetime(latest_d.year, latest_d.month, latest_d.day, tzinfo=max_dt.tzinfo)
        ) + relativedelta(weeks=1)
        earliest_dt = latest_dt - relativedelta(weeks=self.weeks)

        return Bounds(earliest=earliest_dt, latest=latest_dt)

    def _clamp(self, dt: datetime) -> datetime:
        tzinfo = dt.tzinfo if "tzinfo" in dir(dt) else None
        day = datetime(dt.year, dt.month, dt.day, tzinfo=tzinfo)
        return day - relativedelta(days=day.weekday())


class Monthly(Plot):
    def __init__(
        self,
        series: list[Series],
        months: int = 12,
        range_columns: Optional[list[str]] = None,
    ):
        super().__init__(series=series, increments=months, range_columns=range_columns)

        self.months = months

    def _x_formatter(self) -> Formatter:
        return FuncFormatter(lambda d, _: num2date(d).strftime("%b"))

    def _bounds(self, df: pd.DataFrame) -> datetime:
        max_dt = self._max_dt(df)
        latest_d = max_dt.date()

        latest_dt = datetime(
            latest_d.year, latest_d.month, 1, tzinfo=max_dt.tzinfo
        ) + relativedelta(months=1)
        earliest_dt = latest_dt - relativedelta(months=self.months)

        return Bounds(earliest=earliest_dt, latest=latest_dt)

    def _clamp(self, dt: datetime) -> datetime:
        tzinfo = dt.tzinfo if "tzinfo" in dir(dt) else None
        return datetime(dt.year, dt.month, 1, tzinfo=tzinfo)


LINE_STYLES = ["-", "--", "-.", ":"]


class Chart:
    def __init__(
        self,
        title: Optional[str] = None,
        formatter: Formatter | str = StrMethodFormatter("{x:,.0f}"),
        plots: list[type[Plot]] = [],
        height: int = 5,
        width_increment: float = 0.7,
        y_limits: Optional[tuple[float, float]] = None,
    ):
        if isinstance(formatter, str):
            formatter = StrMethodFormatter(formatter)

        self.title = title
        self.formatter = formatter
        self.plots = plots
        self.height = height
        self.width_increment = width_increment
        self.y_limits = y_limits

    def _plots(self, df):
        if not isinstance(df.index, pd.DatetimeIndex):
            raise Exception("dataframe must have a DatetimeIndex")

        if len(self.plots) > 0:
            return self.plots

        # find numeric columns in dataframe
        numeric_columns = df.select_dtypes(include=np.number).columns

        if len(numeric_columns) == 0:
            raise Exception("dataframe must have numeric columns")

        if len(numeric_columns) > len(LINE_STYLES):
            raise Exception(
                f"too many numeric columns ({len(numeric_columns)}) for line styles ({len(LINE_STYLES)})"
            )

        series = [
            Series(
                columns=col,
                label=col,
                agg=np.sum,
                style=SeriesStyle(
                    color="black", linestyle=line_style, marker="o", markersize=0
                ),
            )
            for (col, line_style) in zip(
                numeric_columns,
                LINE_STYLES[: len(numeric_columns)],
            )
        ]

        days_in_index = (df.index.max() - df.index.min()).days

        if days_in_index < 14:
            return [Daily(series=series, days=days_in_index)]
        elif days_in_index < 31:
            return [Daily(series=series, days=7), Weekly(series=series, weeks=4)]
        elif days_in_index < 365:
            return [Daily(series=series, days=7), Weekly(series=series, weeks=6)]
        elif days_in_index >= 365:
            return [
                Daily(series=series, days=7),
                Weekly(series=series, weeks=6),
                Monthly(series=series, months=12),
            ]

    def plot(self, df):
        plots = self._plots(df)

        fig, axs = plt.subplots(
            1,
            len(plots),
            figsize=(
                sum(plot.increments for plot in plots) * self.width_increment,
                self.height,
            ),
            gridspec_kw={"width_ratios": [plot.increments for plot in plots]},
            sharey=True,
        )

        # if there's only one plot, axs is a single axis, not an array
        if len(plots) == 1:
            axs = [axs]

        if self.title is not None:
            fig.suptitle(self.title)

        for pos, ax, plot in zip(range(len(plots)), axs, plots):
            plot._plot(ax, df, self.formatter)

            if self.y_limits is not None:
                ax.set_ylim(self.y_limits)

            if self.formatter is not None:
                ax.yaxis.set_major_formatter(self.formatter)

            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            if pos > 0:
                ax.spines["left"].set_visible(False)
                plt.setp(ax.get_yticklines(), visible=False)

            ax.grid(visible=True, which="major", axis="y", alpha=0.3)
            ax.tick_params(axis="both", which="major", labelsize=9)

            for label in ax.get_xticklabels():
                label.set_fontweight(700)

            _add_legend(ax, [s.label for s in plot.series])

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.12)

        return fig

    def data(self, df):
        return [plot.data(df) for plot in self._plots(df)]


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
