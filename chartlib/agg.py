def ratio(num, denom):
    def fn(row):
        return row[num].sum() / row[denom].sum()

    return fn
