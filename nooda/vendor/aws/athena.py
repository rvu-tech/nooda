import ast
import boto3
import IPython
import pandas
import time
import sys

from datetime import date, datetime
from google.cloud.bigquery.magics import line_arg_parser as lap
from google.cloud.bigquery.dbapi import _helpers
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring


def _parse_athena_col(col, typ):
    val = col.get("VarCharValue", "")

    if typ == "varchar":
        return val
    elif typ == "double":
        return float(val)
    else:
        raise Exception(f"unknown type: {typ}")


def _parse_athena_rows(result_set):
    column_info = result_set["ResultSetMetadata"]["ColumnInfo"]

    out = []
    for row in result_set["Rows"]:
        try:
            out.append(
                {
                    info["Name"]: _parse_athena_col(col, info["Type"])
                    for (col, info) in zip(row["Data"], column_info)
                }
            )
        except Exception as err:
            print(f"failed to parse row: {err}", file=sys.stderr)
            continue

    return out


def _query_athena(
    sql, database, output_location, region="eu-west-1", execution_id=None, profile=None
):
    if profile is not None:
        session = boto3.Session(profile_name=profile)
        client = session.client("athena", region_name=region)
    else:
        client = boto3.client("athena", region_name=region)

    if execution_id is None:
        cost_query_response = client.start_query_execution(
            QueryString=sql,
            QueryExecutionContext={
                "Database": database,
            },
            ResultConfiguration={
                "OutputLocation": output_location,
            },
        )

        execution_id = cost_query_response["QueryExecutionId"]
        finished = False

        while not finished:
            status_response = client.get_query_execution(QueryExecutionId=execution_id)

            if status_response["QueryExecution"]["Status"]["State"] in (
                "SUCCEEDED",
                "FAILED",
                "CANCELLED",
            ):
                finished = True
            else:
                time.sleep(5)

    rows = []
    cost_result_response = client.get_query_results(
        QueryExecutionId=execution_id,
    )

    while cost_result_response is not None:
        rows = rows + _parse_athena_rows(cost_result_response["ResultSet"])

        if "NextToken" in cost_result_response:
            cost_result_response = client.get_query_results(
                QueryExecutionId=execution_id,
                NextToken=cost_result_response["NextToken"],
            )
        else:
            cost_result_response = None

    return rows


@magic_arguments()
@argument("var", type=str, help="the var to put the dataframe into", nargs="?")
@argument("--database", type=str, help="athena database")
@argument("--output_location", type=str, help="s3 url to store results")
@argument("--profile", type=str, help="aws profile to use")
@argument(
    "--params",
    nargs="+",
    default=None,
    help=(
        "Parameters to format the query string. If present, the --params "
        "flag should be followed by a string representation of a dictionary "
        "in the format {'param_name': 'param_value'} (ex. {\"num\": 17}), "
        "or a reference to a dictionary in the same format. The dictionary "
        "reference can be made by including a '$' before the variable "
        "name (ex. $my_dict_var)."
    ),
)
def _cell_magic(line, cell):
    # This arg parsing code is copied from the google.cloud.bigquery.magic

    # The built-in parser does not recognize Python structures such as dicts, thus
    # we extract the "--params" option and inteprpret it separately.
    try:
        params_option_value, rest_of_args = _split_args_line(line)
    except lap.exceptions.QueryParamsParseError as exc:
        rebranded_error = SyntaxError(
            "--params is not a correctly formatted JSON string or a JSON "
            "serializable dictionary"
        )
        raise rebranded_error from exc
    except lap.exceptions.DuplicateQueryParamsError as exc:
        rebranded_error = ValueError("Duplicate --params option.")
        raise rebranded_error from exc
    except lap.exceptions.ParseError as exc:
        rebranded_error = ValueError(
            "Unrecognized input, are option values correct? "
            "Error details: {}".format(exc.args[0])
        )
        raise rebranded_error from exc

    args = parse_argstring(_cell_magic, rest_of_args)

    params = []
    if params_option_value:
        # A non-existing params variable is not expanded and ends up in the input
        # in its raw form, e.g. "$query_params".
        if params_option_value.startswith("$"):
            msg = 'Parameter expansion failed, undefined variable "{}".'.format(
                params_option_value[1:]
            )
            raise NameError(msg)

        params = _helpers.to_query_parameters(ast.literal_eval(params_option_value), {})

    if args.var is not None and not args.var.isidentifier():
        raise NameError(f"Expecting an identifier, not {args.var}")

    # do some gnarly string replacing to add the params
    query = cell
    for param in params:
        query = query.replace(f"@{param.name}", _sql_value_for(param.value))

    results = _query_athena(
        query, args.database, args.output_location, profile=args.profile
    )

    df = pandas.DataFrame(data=results)

    if args.var is not None:
        IPython.get_ipython().push({args.var: df})
    else:
        return df


def _sql_value_for(v):
    if isinstance(v, str):
        try:
            v_date = datetime.strptime(v, "%Y-%m-%d")
            return f"date '{v_date.strftime('%Y-%m-%d')}'"
        except ValueError:
            pass

        return f"'{v}'"
    elif isinstance(v, int):
        return f"{v}"
    else:
        raise Exception(f"unknown type: {type(v)}")


def _split_args_line(line):
    """Split out the --params option value from the input line arguments.

    Args:
        line (str): The line arguments passed to the cell magic.

    Returns:
        Tuple[str, str]
    """
    lexer = lap.Lexer(line)
    scanner = lap.Parser(lexer)
    tree = scanner.input_line()

    extractor = lap.QueryParamsExtractor()
    params_option_value, rest_of_args = extractor.visit(tree)

    return params_option_value, rest_of_args


def load_ipython_extension(ipython):
    """Called by IPython when this module is loaded as an IPython extension."""

    ipython.register_magic_function(_cell_magic, magic_kind="cell", magic_name="athena")
