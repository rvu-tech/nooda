import pandas as pd
import requests

_BASE_URL = "https://api.incident.io/v2"


def _headers(api_key):
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _paginated_get(api_key, path, params=None):
    params = dict(params or {})
    params["page_size"] = 250
    items = []

    while True:
        resp = requests.get(
            f"{_BASE_URL}{path}", headers=_headers(api_key), params=params
        )
        resp.raise_for_status()
        data = resp.json()

        for value in data.values():
            if isinstance(value, list):
                items.extend(value)
                break

        after = data.get("pagination_meta", {}).get("after")
        if not after:
            break
        params["after"] = after

    return items


def _resolve_custom_field(api_key, field_name):
    resp = requests.get(f"{_BASE_URL}/custom_fields", headers=_headers(api_key))
    resp.raise_for_status()
    field_id = None
    for field in resp.json().get("custom_fields", []):
        if field["name"].lower() == field_name.lower():
            field_id = field["id"]
            break
    if not field_id:
        raise ValueError(f"Custom field '{field_name}' not found")

    base_v1 = _BASE_URL.replace("/v2", "/v1")
    options = {}
    params = {"custom_field_id": field_id, "page_size": 250}
    while True:
        resp = requests.get(
            f"{base_v1}/custom_field_options",
            headers=_headers(api_key),
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()
        for opt in data.get("custom_field_options", []):
            options[opt["value"].lower()] = opt["id"]
        after = data.get("pagination_meta", {}).get("after")
        if not after:
            break
        params["after"] = after

    return field_id, options


def _slugify(s):
    return s.lower().replace(" ", "_")


def _build_dataframe(incidents):
    rows = []
    for inc in incidents:
        row = {
            "id": inc.get("id"),
            "reference": inc.get("reference"),
            "name": inc.get("name"),
            "severity": (
                inc.get("severity", {}).get("name") if inc.get("severity") else None
            ),
            "created_at": inc.get("created_at"),
        }

        for tsv in inc.get("incident_timestamp_values", []):
            col_name = _slugify(tsv["incident_timestamp"]["name"])
            row[col_name] = tsv.get("value", {}).get("value")

        for dm in inc.get("duration_metrics", []):
            col_name = f"{_slugify(dm['duration_metric'].get('name', 'unknown'))}_seconds"
            row[col_name] = dm.get("value_seconds")

        rows.append(row)

    return pd.DataFrame(rows)


def fetch_incidents(
    api_key,
    *,
    severity=None,
    date_from=None,
    date_to=None,
    incident_type=None,
    custom_fields=None,
    modes=("standard", "retrospective"),
):
    """Fetch closed incidents from incident.io and return a DataFrame.

    Args:
        api_key: incident.io API key.
        severity: List of severity names to filter on, or None for all.
        date_from: ISO 8601 lower bound on created_at, or None.
        date_to: ISO 8601 upper bound on created_at, or None.
        incident_type: List of incident type names, or None.
        custom_fields: Dict mapping custom field names to lists of option values
            to filter on. e.g. {"Affected brand": ["Tempcover"]}.
        modes: Sequence of incident modes, or None/empty to skip.
    """
    params = {"status_category[one_of]": ["closed"]}

    if modes:
        params["mode[one_of]"] = list(modes)

    if severity:
        params["severity[one_of]"] = list(severity)

    if date_from:
        params["created_at[gte]"] = date_from
    if date_to:
        params["created_at[lte]"] = date_to

    if incident_type:
        params["incident_type[one_of]"] = list(incident_type)

    if custom_fields:
        for field_name, values in custom_fields.items():
            field_id, option_map = _resolve_custom_field(api_key, field_name)
            option_ids = []
            for val in values:
                opt_id = option_map.get(val.lower())
                if not opt_id:
                    raise ValueError(
                        f"Option '{val}' not found for '{field_name}'. "
                        f"Available: {list(option_map)}"
                    )
                option_ids.append(opt_id)
            params[f"custom_field[{field_id}][one_of]"] = option_ids

    incidents = _paginated_get(api_key, "/incidents", params)
    return _build_dataframe(incidents)


def list_timestamp_types(api_key):
    """Return the configured incident timestamp types as a list of dicts."""
    resp = requests.get(
        f"{_BASE_URL}/incident_timestamps", headers=_headers(api_key)
    )
    resp.raise_for_status()
    return resp.json().get("incident_timestamps", [])
