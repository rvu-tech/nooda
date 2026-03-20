from datetime import datetime, timedelta, timezone

import pandas as pd
import requests


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _query_range(grafana_url, token, datasource_uid, expr, start, end, step):
    url = (
        f"{grafana_url}/api/datasources/proxy/uid/{datasource_uid}"
        f"/api/v1/query_range"
    )
    resp = requests.get(
        url,
        headers=_headers(token),
        params={"query": expr, "start": start, "end": end, "step": step},
    )
    resp.raise_for_status()
    return resp.json()


def _build_dataframe(query_results):
    merged = None

    for name, response in query_results:
        data = response.get("data", {})
        if data.get("resultType") != "matrix":
            continue

        results = data.get("result", [])
        if not results:
            continue

        for i, series in enumerate(results):
            values = series.get("values", [])
            if not values:
                continue

            col = name if len(results) == 1 else f"{name}_{i}"
            timestamps = [
                datetime.fromtimestamp(v[0], tz=timezone.utc) for v in values
            ]
            floats = [float(v[1]) for v in values]

            df = pd.DataFrame({"timestamp": timestamps, col: floats})

            if merged is None:
                merged = df
            else:
                merged = merged.merge(df, on="timestamp", how="outer")

    if merged is not None:
        merged.sort_values("timestamp", inplace=True)
        merged.reset_index(drop=True, inplace=True)

    return merged if merged is not None else pd.DataFrame()


def query_metrics(
    token,
    grafana_url,
    datasource_uid,
    queries,
    *,
    time_from=None,
    time_to=None,
    step="5m",
):
    """Run PromQL queries via Grafana Cloud and return a DataFrame.

    Args:
        token: Grafana Service Account token.
        datasource_uid: UID of the Prometheus/Mimir datasource.
        queries: List of {"name": str, "expr": str} dicts.
        grafana_url: Grafana instance base URL.
        time_from: ISO 8601 start time, or None for 24h ago.
        time_to: ISO 8601 end time, or None for now.
        step: Query resolution step (e.g. "5m", "1h").
    """
    now = datetime.now(timezone.utc)
    start = time_from or (now - timedelta(hours=24)).isoformat()
    end = time_to or now.isoformat()

    results = []
    for q in queries:
        resp = _query_range(
            grafana_url, token, datasource_uid, q["expr"], start, end, step
        )
        results.append((q["name"], resp))

    return _build_dataframe(results)


def list_datasources(grafana_url, token, *):
    """Return available datasources as a list of dicts (uid, type, name, etc.)."""
    resp = requests.get(
        f"{grafana_url}/api/datasources", headers=_headers(token)
    )
    resp.raise_for_status()
    return resp.json()
