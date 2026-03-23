from unittest.mock import patch, MagicMock

from nooda.slack.send import send


def test_send_does_not_leak_token(capsys):
    mock_client = MagicMock()
    mock_client.chat_postMessage.return_value = {"ts": "123"}

    with patch("nooda.slack.send.WebClient", return_value=mock_client):
        send("#test", "hello", token="super-secret-token")

    captured = capsys.readouterr()
    assert "super-secret-token" not in captured.err
