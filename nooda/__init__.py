from .chart.ops import Chart


def FinancialFormatter(symbol="$", dp=0):
    return symbol + "{x:,." + str(dp) + "f}"
