import sys
from unittest.mock import MagicMock

# Mock undeclared dependencies so we can import the pure functions
for mod in [
    "boto3",
    "google",
    "google.cloud",
    "google.cloud.bigquery",
    "google.cloud.bigquery.magics",
    "google.cloud.bigquery.magics.line_arg_parser",
    "google.cloud.bigquery.dbapi",
    "google.cloud.bigquery.dbapi._helpers",
]:
    sys.modules.setdefault(mod, MagicMock())

from nooda.vendor.aws.athena import _sql_value_for


def test_sql_value_for_escapes_single_quotes():
    assert _sql_value_for("O'Brien") == "'O''Brien'"


def test_sql_value_for_plain_string():
    assert _sql_value_for("hello") == "'hello'"


def test_sql_value_for_integer():
    assert _sql_value_for(42) == "42"


def test_sql_value_for_date_string():
    assert _sql_value_for("2023-01-15") == "date '2023-01-15'"
