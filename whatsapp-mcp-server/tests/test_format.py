"""Tests for format_message and format_messages_list return types and content."""
from datetime import datetime
from unittest.mock import patch

from whatsapp_mcp_server import Message, format_message, format_messages_list


@patch("whatsapp_mcp_server.whatsapp.get_sender_name", return_value="Alice")
def test_format_message_returns_str(mock_get_sender):
    """format_message returns a string, not None."""
    msg = Message(
        timestamp=datetime(2025, 1, 15, 12, 0, 0),
        sender="1234567890",
        content="Hello",
        is_from_me=False,
        chat_jid="1234567890@s.whatsapp.net",
        id="msg-1",
        chat_name="Alice",
    )
    result = format_message(msg, show_chat_info=True)
    assert isinstance(result, str)
    assert "Hello" in result
    assert "Alice" in result


def test_format_messages_list_returns_str_empty():
    """format_messages_list returns a string for empty list."""
    result = format_messages_list([], show_chat_info=True)
    assert isinstance(result, str)
    assert "No messages" in result


@patch("whatsapp_mcp_server.whatsapp.get_sender_name", return_value="Bob")
def test_format_messages_list_returns_str_with_messages(mock_get_sender):
    """format_messages_list returns a string for a list of messages."""
    msg = Message(
        timestamp=datetime(2025, 1, 15, 12, 0, 0),
        sender="1234567890",
        content="Hi",
        is_from_me=False,
        chat_jid="1234567890@s.whatsapp.net",
        id="msg-1",
    )
    result = format_messages_list([msg], show_chat_info=False)
    assert isinstance(result, str)
    assert "Hi" in result
