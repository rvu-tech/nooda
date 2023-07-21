import pandas as pd

from datetime import timedelta
from dateutil import relativedelta
from matplotlib.ticker import FuncFormatter


def _hours_to_day_hours(hours, *args):
    delta = timedelta(hours=hours)
    hours = round(delta.seconds / (60 * 60))

    return f"{delta.days}d {hours}h"


hours_to_day_hours = FuncFormatter(_hours_to_day_hours)


def _seconds_to_day_hours(seconds, *args):
    delta = timedelta(seconds=seconds)
    hours = round(delta.seconds / (60 * 60))

    return f"{delta.days}d {hours}h"


seconds_to_day_hours = FuncFormatter(_seconds_to_day_hours)


def human_readable_delta(delta: relativedelta) -> str:
    attrs = ["years", "months", "days", "hours", "minutes", "seconds"]
    human_readable = [
        "%d %s"
        % (getattr(delta, attr), attr if getattr(delta, attr) > 1 else attr[:-1])
        for attr in attrs
        if getattr(delta, attr)
    ]

    return ", ".join(human_readable)
