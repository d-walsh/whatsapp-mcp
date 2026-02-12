"""
WhatsApp MCP Server – use as MCP server or as a Python library.

Use as a library (e.g. in Codex skills or scripts) to read/send WhatsApp
without going through the MCP/LLM, saving tokens and latency.
"""

from whatsapp_mcp_server.whatsapp import (
    Message,
    Chat,
    Contact,
    MessageContext,
    Reaction,
    search_contacts,
    list_messages,
    list_chats,
    get_chat,
    get_direct_chat_by_contact,
    get_contact_chats,
    get_last_interaction,
    get_message_context,
    get_reactions,
    send_message,
    send_file,
    send_audio_message,
    send_reaction,
    download_media,
    format_message,
    format_messages_list,
)
from whatsapp_mcp_server import audio  # noqa: F401

__all__ = [
    "Message",
    "Chat",
    "Contact",
    "MessageContext",
    "Reaction",
    "search_contacts",
    "list_messages",
    "list_chats",
    "get_chat",
    "get_direct_chat_by_contact",
    "get_contact_chats",
    "get_last_interaction",
    "get_message_context",
    "get_reactions",
    "send_message",
    "send_file",
    "send_audio_message",
    "send_reaction",
    "download_media",
    "format_message",
    "format_messages_list",
    "audio",
]
