"""Tests for send_message with mocked HTTP (no real bridge)."""
from unittest.mock import patch

from whatsapp_mcp_server import send_message


def test_send_message_returns_tuple_with_success_and_message():
    """send_message returns (bool, str) and respects mocked API response."""
    with patch("whatsapp_mcp_server.whatsapp.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "success": True,
            "message": "Message sent to 1234567890",
        }
        success, status_message = send_message("1234567890", "Hello")
        assert success is True
        assert isinstance(status_message, str)
        assert "sent" in status_message or "1234567890" in status_message


def test_send_message_handles_api_failure():
    """send_message returns (False, message) when API returns success: false."""
    with patch("whatsapp_mcp_server.whatsapp.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "success": False,
            "message": "Not connected to WhatsApp",
        }
        success, status_message = send_message("1234567890", "Hello")
        assert success is False
        assert isinstance(status_message, str)
