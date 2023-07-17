import IPython
import io
import json
import nooda.publish
import os

from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring

from nooda.vendor.databricks import running_in_databricks, notebook_path


@magic_arguments()
@argument("-u", "--url", help="A URL to the nooda.publish server")
@argument("thing_id", type=str, help="id to publish to")
def _line_magic(line):
    args = parse_argstring(_line_magic, line)

    if running_in_databricks():
        path = notebook_path()
        print(path)
    else:
        raise NotImplementedError("Only works in Databricks for now")
