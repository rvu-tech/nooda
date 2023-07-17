from dateutil.relativedelta import relativedelta


def ratio(num, denom):
    def fn(row):
        return row[num].sum() / row[denom].sum()

    return fn


def avg_daily(xs):
    days = relativedelta(xs.index.max(), xs.index.min()).days + 1
    return xs.sum() / days
