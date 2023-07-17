import IPython
import io
import json
import nooda.publish
import os

from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring
from IPython.display import display
from nooda.vendor.databricks import running_in_databricks, notebook_url

from .send import send


MIME_TYPE = "application/vnd.nooda.slack+json"


@magic_arguments()
@argument("-u", "--url", help="A URL to reference this notebook")
@argument("channel", type=str, help="the channel to send the message to")
@argument("var", type=str, help="the var to send to slack")
def _line_magic(line):
    args = parse_argstring(_line_magic, line)

    if not args.var.isidentifier():
        raise NameError(f"Expecting an identifier, not {args.var}")

    ip = IPython.get_ipython()
    val = ip.user_ns.get(args.var, ip)  # ip serves as a sentinel

    url = args.url
    if url is None and running_in_databricks():
        url = notebook_url()

    response = send(args.channel, val, back_url=url)

    display(
        {
            MIME_TYPE: json.dumps(response._asdict()),
        },
        raw=True,
        metadata={
            MIME_TYPE: {},
        },
        include=[MIME_TYPE],
    )
