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