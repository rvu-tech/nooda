import IPython
import io
import json
import nooda.publish
import os
import sys

from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring
from IPython.display import display
from nooda.vendor.databricks import running_in_databricks, notebook_url

from .send import send


LAST_RESPONSE_VAR = "__slack_last_response"
MIME_TYPE = "application/vnd.nooda.slack+json"


def _var_or_string(raw, ip):
    out = None

    if raw is not None:
        if raw.isidentifier():
            out = ip.user_ns.get(raw, ip)
            if out is ip:
                raise NameError(f"Undefined variable {raw}")
            elif out is None:
                raise ValueError(f"Variable {raw} is None")
        elif raw.startswith('"') and raw.endswith('"'):
            out = raw[1:-1]
        elif raw.startswith("'") and raw.endswith("'"):
            out = raw[1:-1]
        else:
            raise NameError(f"Expecting an identifier or quoted string, not {raw}")

    return out


@magic_arguments()
@argument(
    "--markdown",
    help="A var that contains slack mrkdwn to append if sending a file",
    default=None,
)
@argument(
    "--token",
    help="Pass the token in via an argument instead of the SLACK_TOKEN env var",
    default=None,
)
@argument(
    "channel",
    type=str,
    help="the channel to send the message to. empty string will skip",
)
@argument("message", type=str, help="the var or string to send to slack")
def _slack_line_magic(line):
    args = parse_argstring(_slack_line_magic, line)

    ip = IPython.get_ipython()

    channel = _var_or_string(args.channel, ip)
    message = _var_or_string(args.message, ip)
    markdown = _var_or_string(args.markdown, ip)
    token = _var_or_string(args.token, ip)

    response = send(channel, message, markdown=markdown, token=token)

    ip.user_ns[LAST_RESPONSE_VAR] = response
    if response.successful:
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


@magic_arguments()
@argument(
    "--markdown",
    help="A var that contains slack mrkdwn to append if sending a file",
    default=None,
)
@argument("message", type=str, help="the var or string to send to slack")
def _slack_thread_line_magic(line):
    args = parse_argstring(_slack_thread_line_magic, line)
    ip = IPython.get_ipython()

    last_response = ip.user_ns.get(LAST_RESPONSE_VAR, None)
    if last_response is None:
        raise ValueError("No previous response to reply to, use %slack first")

    message = _var_or_string(args.message, ip)
    markdown = _var_or_string(args.markdown, ip)

    send(
        last_response.channel,
        message,
        markdown=markdown,
        thread_ts=last_response.ts,
        token=last_response.token,
    )
