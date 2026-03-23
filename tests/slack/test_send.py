import pytest

from unittest.mock import patch, MagicMock

from nooda.slack.send import send


def test_send_does_not_leak_token(capsys):
    mock_client = MagicMock()
    mock_client.chat_postMessage.return_value = {"ts": "123"}

    with patch("nooda.slack.send.WebClient", return_value=mock_client):
        send("#test", "hello", token="super-secret-token")

    captured = capsys.readouterr()
    assert "super-secret-token" not in captured.err


def test_send_file_upload_does_not_poll_forever():
    """File upload polling should give up after a bounded number of retries."""
    mock_fig = MagicMock(spec=["savefig"])

    mock_client = MagicMock()
    mock_client.files_upload_v2.return_value = {"files": [{"id": "F123"}]}
    mock_client.files_info.return_value = {"file": {"shares": {}}}

    sleep_count = 0

    def counting_sleep(seconds):
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count > 50:
            raise TimeoutError("Polling exceeded 50 iterations")

    with patch("nooda.slack.send.WebClient", return_value=mock_client):
        with patch("nooda.slack.send.time") as mock_time:
            mock_time.sleep = counting_sleep
            try:
                send("#test", mock_fig, token="tok")
            except TimeoutError:
                pytest.fail("send() polled more than 50 times -- infinite loop")

    assert mock_client.files_info.call_count <= 50
