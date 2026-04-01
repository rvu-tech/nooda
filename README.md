# nooda

OODA, notebooks style.

This brings together charts, slack integration and a publishing 
tool.


## Usage

If you're using poetry you can add this library as follows:

```
$ poetry add git+https://github.com/rvu-tech/nooda.git
```

You can find an example of how to plot a chart in `example.ipynb`.


```
import pandas as pd
import numpy as np

import nooda

data = pd.DataFrame(
    data={
        "day": pd.date_range(start="2021-07-01", end="2023-07-09", freq="D"),
    }
)
data["value"] = np.random.randint(10000, 100000, data.shape[0])

nooda.Chart().plot(data.set_index("day"))
```

### Querying Grafana

#### Prometheus / Mimir metrics

```python
from nooda.vendor.grafana import query_metrics

df = query_metrics(
    token="glsa_...",
    grafana_url="https://grafana.example.com",
    datasource_uid="prometheus-uid",
    queries=[
        {"name": "requests", "expr": 'sum(rate(http_requests_total[5m]))'},
    ],
    step="5m",
)
```

#### Loki logs

```python
from nooda.vendor.grafana import query_logs

# Log stream query
df = query_logs(
    token="glsa_...",
    grafana_url="https://grafana.example.com",
    datasource_uid="loki-uid",
    query='{app="web"} |= "error"',
)
# Returns DataFrame with: timestamp, line, and label columns

# Metric query over logs
df = query_logs(
    token="glsa_...",
    grafana_url="https://grafana.example.com",
    datasource_uid="loki-uid",
    query='rate({app="web"} |= "error" [5m])',
    step="1m",
)
# Returns DataFrame with: timestamp, value, and label columns
```

### Selecting views

By default, nooda auto-selects which time views (daily, weekly, monthly) to show
based on the date range of your data. You can override this with the `views` parameter:

```python
# Show only daily and monthly
nooda.plot(df, views=["daily", "monthly"])

# Works with ratio_plot too
chart = nooda.ratio_plot("num_valid", "total_num", views=["weekly"])
chart.plot(df)
```

Valid views: `"daily"`, `"weekly"`, `"monthly"`.

### Controlling comparison series

`ratio_plot` shows Week-over-Week (WoW) and Year-over-Year (YoY) comparison series by default on daily and monthly views respectively. You can disable either:

```python
# Hide WoW on daily views
chart = nooda.ratio_plot("num_valid", "total_num", show_wow=False)
chart.plot(df)

# Hide YoY on monthly views
chart = nooda.ratio_plot("num_valid", "total_num", show_yoy=False)
chart.plot(df)
```

### Hiding the legend

The legend is shown by default. To hide it, pass `show_legend=False`:

```python
nooda.plot(df, show_legend=False)

# Works with ratio_plot too
chart = nooda.ratio_plot("num_valid", "total_num", show_legend=False)
chart.plot(df)
```