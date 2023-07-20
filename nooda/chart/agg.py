import pandas as pd

from dateutil.relativedelta import relativedelta


def ratio(num, denom):
    def fn(row):
        return row[num].sum() / row[denom].sum()

    return fn


def avg_daily(xs):
    if isinstance(xs, pd.Series):
        vals = xs[xs.isna() == False]
    else:
        assert len(xs.columns) == 1  # only expect frames with one column
        vals = xs[xs.isna().any(axis=1) == False]

    max_dt = vals.index.max()
    if max_dt is pd.NaT:
        return None

    days = (max_dt - vals.index.min()).days + 1
    return vals.sum() / days


def p(percentile):
    def fn(xs):
        return xs.quantile(percentile / 100)

    return fn
