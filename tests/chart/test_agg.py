import numpy as np
import pandas as pd
import pytest

from datetime import datetime
from nooda.chart.agg import avg_daily


def _clamp_to_month(dt: datetime) -> datetime:
    return datetime(dt.year, dt.month, 1)


def test_avg_daily():
    df = pd.DataFrame(
        data={
            "day": pd.date_range("2023-01-01", "2023-03-31"),
        }
    )
    df["full"] = np.repeat(3, df.shape[0])
    df["na"] = np.concatenate(
        (np.repeat(3, df.shape[0] / 2), np.repeat(pd.NA, df.shape[0] / 2))
    )
    df.set_index("day", inplace=True)

    # test with single array of columns vs one column name
    # this ends up passing different things through to the agg function

    na_avg_series = df.groupby(_clamp_to_month)["na"].apply(avg_daily).dropna()

    assert na_avg_series[datetime(2023, 2, 1)] == 3
    with pytest.raises(KeyError):
        na_avg_series[datetime(2023, 3, 1)]

    na_avg_df = df.groupby(_clamp_to_month)[["na"]].apply(avg_daily).dropna()

    assert na_avg_df.loc[datetime(2023, 2, 1)].sum() == 3
    with pytest.raises(KeyError):
        na_avg_df.loc[datetime(2023, 3, 1)]

    full_avg = df.groupby(_clamp_to_month)["full"].apply(avg_daily).dropna()

    assert full_avg[datetime(2023, 3, 1)] == 3
    with pytest.raises(KeyError):
        full_avg[datetime(2023, 4, 1)]
