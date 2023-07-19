import io
import os
import sys

from collections import namedtuple
from slack_sdk import WebClient
from typing import Optional, Any


def get_file_thread(file, channel_id):
    shares = file["shares"]

    channel_share = shares.get("private", {}).get(channel_id, [])
    if len(channel_share) == 0:
        channel_share = shares.get("public", {}).get(channel_id, [])

    if len(channel_share) == 0:
        return None

    return channel_share[0]["ts"]


Response = namedtuple("Response", ["channel", "ts", "back_url"])


def send(channel: str, val: Any, back_url: Optional[str] = None) -> Optional[Response]:
    slack_token = os.getenv("SLACK_TOKEN")

    if slack_token is None:
        print("SLACK_TOKEN not set, skipping slack send", file=sys.stderr)
        return None

    slack_client = WebClient(token=os.getenv("SLACK_TOKEN"))

    ts = None

    if isinstance(val, str):
        message_response = slack_client.chat_postMessage(
            channel=channel,
            text=val,
        )

        ts = message_response["ts"]
    elif "savefig" in dir(val):
        # save the chart into a byte buffer
        buf = io.BytesIO()
        val.savefig(buf, format="png", dpi=100)
        buf.seek(0)

        slack_client.files_upload_v2(
            channel=channel,
            file=buf.read(),
        )

        while ts is None:
            # the message thread associated with the file upload isn't reliaibly in
            # the response. yay eventual consistency!
            time.sleep(2)

            file_response = slack_client.files_info(
                file=upload_response["files"][0]["id"]
            )
            ts = get_file_thread(file_response["file"], channel)
    else:
        raise TypeError(f"unsupported type: {type(val)}")

    return Response(channel, ts, back_url)
