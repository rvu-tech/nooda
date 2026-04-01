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
    if resp.status_code == 400:
        print(f"Grafana 400 Bad Request: {resp.text}")
    resp.raise_for_status()
    return resp.json()


def _build_dataframe(query_results, truncate=None):
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
            if truncate:
                timestamps = [ts.floor(truncate) for ts in pd.to_datetime(timestamps)]
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


def _loki_query_range(grafana_url, token, datasource_uid, query, start, end, limit, step):
    url = (
        f"{grafana_url}/api/datasources/proxy/uid/{datasource_uid}"
        f"/loki/api/v1/query_range"
    )
    params = {"query": query, "start": start, "end": end, "limit": limit}
    if step:
        params["step"] = step
    resp = requests.get(url, headers=_headers(token), params=params)
    if resp.status_code == 400:
        print(f"Grafana 400 Bad Request: {resp.text}")
    resp.raise_for_status()
    return resp.json()


def _build_loki_dataframe(response):
    data = response.get("data", {})
    result_type = data.get("resultType")
    results = data.get("result", [])

    if not results:
        return pd.DataFrame()

    if result_type == "streams":
        rows = []
        for stream in results:
            labels = stream.get("stream", {})
            for ts_ns, line in stream.get("values", []):
                ts = datetime.fromtimestamp(int(ts_ns) / 1e9, tz=timezone.utc)
                rows.append({"timestamp": ts, "line": line, **labels})
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    if result_type == "matrix":
        rows = []
        for series in results:
            labels = series.get("metric", {})
            for ts, val in series.get("values", []):
                rows.append({
                    "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc),
                    "value": float(val),
                    **labels,
                })
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    return pd.DataFrame()


def query_metrics(
    token,
    grafana_url,
    datasource_uid,
    queries,
    *,
    time_from=None,
    time_to=None,
    step="5m",
    truncate=None,
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
        truncate: Pandas frequency string to floor timestamps (e.g. "1D", "1h").
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

    return _build_dataframe(results, truncate=truncate)


def query_logs(
    token,
    grafana_url,
    datasource_uid,
    query,
    *,
    time_from=None,
    time_to=None,
    limit=1000,
    step=None,
):
    """Run a LogQL query via Grafana Cloud and return a DataFrame.

    Args:
        token: Grafana Service Account token.
        grafana_url: Grafana instance base URL.
        datasource_uid: UID of the Loki datasource.
        query: LogQL expression string.
        time_from: ISO 8601 start time, or None for 1h ago.
        time_to: ISO 8601 end time, or None for now.
        limit: Max log lines for stream queries.
        step: Resolution step for metric queries (e.g. "1m").
    """
    now = datetime.now(timezone.utc)
    start = time_from or (now - timedelta(hours=1)).isoformat()
    end = time_to or now.isoformat()

    resp = _loki_query_range(
        grafana_url, token, datasource_uid, query, start, end, limit, step
    )
    return _build_loki_dataframe(resp)


def list_datasources(grafana_url, token):
    """Return available datasources as a list of dicts (uid, type, name, etc.)."""
    resp = requests.get(
        f"{grafana_url}/api/datasources", headers=_headers(token)
    )
    resp.raise_for_status()
    return resp.json()
