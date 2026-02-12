# WhatsApp MCP Server

This is a Model Context Protocol (MCP) server for WhatsApp.

With this you can search and read your personal Whatsapp messages (including images, videos, documents, and audio messages), search your contacts and send messages to either individuals or groups. You can also send media files including images, videos, documents, and audio messages. You can read and send message reactions (e.g. thumbs up, heart).

It connects to your **personal WhatsApp account** directly via the Whatsapp web multidevice API (using the [whatsmeow](https://github.com/tulir/whatsmeow) library). All your messages are stored locally in a SQLite database and only sent to an LLM (such as Claude) when the agent accesses them through tools (which you control).

Here's an example of what you can do when it's connected to Claude.

![WhatsApp MCP](./example-use.png)

> To get updates on this and other projects I work on [enter your email here](https://docs.google.com/forms/d/1rTF9wMBTN0vPfzWuQa2BjfGKdKIpTbyeKxhPMcEzgyI/preview)

> *Caution:* as with many MCP servers, the WhatsApp MCP is subject to [the lethal trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/). This means that project injection could lead to private data exfiltration.

## Installation

### Prerequisites

- Go
- Python 3.11+
- Anthropic Claude Desktop app (or Cursor)
- UV (Python package manager); install with `curl -LsSf https://astral.sh/uv/install.sh | sh` and ensure `uv` is on your PATH
- FFmpeg (_optional_) - Only needed for audio messages. If you want to send audio files as playable WhatsApp voice messages, they must be in `.ogg` Opus format. With FFmpeg installed, the MCP server will automatically convert non-Opus audio files. Without FFmpeg, you can still send raw audio files using the `send_file` tool.

### Steps

1. **Clone this repository**

   ```bash
   git clone https://github.com/lharries/whatsapp-mcp.git
   cd whatsapp-mcp
   ```

2. **Run the WhatsApp bridge**

   Navigate to the whatsapp-bridge directory and run the Go application:

   ```bash
   cd whatsapp-bridge
   go run main.go
   ```

   The first time you run it, you will be prompted to scan a QR code. Scan the QR code with your WhatsApp mobile app to authenticate.

   After approximately 20 days, you will might need to re-authenticate.

3. **Connect to the MCP server**

   Copy the below json with the appropriate {{PATH}} values:

   ```json
   {
     "mcpServers": {
       "whatsapp": {
         "command": "{{PATH_TO_UV}}", // Run `which uv` and place the output here
         "args": [
           "--directory",
           "{{PATH_TO_SRC}}/whatsapp-mcp/whatsapp-mcp-server", // cd into the repo, run `pwd` and enter the output here + "/whatsapp-mcp-server"
           "run",
           "main.py"
         ]
       }
     }
   }
   ```

   For **Claude**, save this as `claude_desktop_config.json` in your Claude Desktop configuration directory at:

   ```
   ~/Library/Application Support/Claude/claude_desktop_config.json
   ```

   For **Cursor**, save this as `mcp.json` in your Cursor configuration directory at:

   ```
   ~/.cursor/mcp.json
   ```

4. **Restart Claude Desktop / Cursor**

   Open Claude Desktop and you should now see WhatsApp as an available integration.

   Or restart Cursor.

### Windows Compatibility

If you're running this project on Windows, be aware that `go-sqlite3` requires **CGO to be enabled** in order to compile and work properly. By default, **CGO is disabled on Windows**, so you need to explicitly enable it and have a C compiler installed.

#### Steps to get it working:

1. **Install a C compiler**  
   We recommend using [MSYS2](https://www.msys2.org/) to install a C compiler for Windows. After installing MSYS2, make sure to add the `ucrt64\bin` folder to your `PATH`.  
   → A step-by-step guide is available [here](https://code.visualstudio.com/docs/cpp/config-mingw).

2. **Enable CGO and run the app**

   ```bash
   cd whatsapp-bridge
   go env -w CGO_ENABLED=1
   go run main.go
   ```

Without this setup, you'll likely run into errors like:

> `Binary was compiled with 'CGO_ENABLED=0', go-sqlite3 requires cgo to work.`

## Architecture Overview

This application consists of two main components:

1. **Go WhatsApp Bridge** (`whatsapp-bridge/`): A Go application that connects to WhatsApp's web API, handles authentication via QR code, and stores message history in SQLite. It serves as the bridge between WhatsApp and the MCP server.

2. **Python MCP Server** (`whatsapp-mcp-server/`): A Python server implementing the Model Context Protocol (MCP), which provides standardized tools for Claude to interact with WhatsApp data and send/receive messages.

### Data Storage

- All message history is stored in a SQLite database within the `whatsapp-bridge/store/` directory
- The database maintains tables for chats and messages
- Messages are indexed for efficient searching and retrieval

### Environment variables (Python MCP server)

You can override defaults so the MCP server works with a different DB path or bridge URL (e.g. if the bridge runs on another host or port):

- **`WHATSAPP_MESSAGES_DB`** – Path to `messages.db` (default: repo layout `whatsapp-bridge/store/messages.db` relative to the server package).
- **`WHATSAPP_API_BASE_URL`** – Bridge REST API base URL (default: `http://localhost:8080/api`). Must match the host and port where the Go bridge is running.

The Go bridge reads:

- **`WHATSAPP_BRIDGE_PORT`** – Port for the bridge REST API (default: `8080`). If you change this, set `WHATSAPP_API_BASE_URL` in the MCP server to the same host and port (e.g. `http://localhost:9090/api`).

## Usage

Once connected, you can interact with your WhatsApp contacts through Claude, leveraging Claude's AI capabilities in your WhatsApp conversations.

### Using as a Python library (no AI / no MCP)

You can use the WhatsApp logic directly from Python (e.g. scripts, Codex/Claude Code skills, cron jobs) without running the MCP server or any LLM. The WhatsApp bridge (Go app) and its SQLite store must still be running; the library talks to the same bridge and database.

Install the server package in editable mode from the repo (from the `whatsapp-mcp` root):

```bash
cd whatsapp-mcp/whatsapp-mcp-server
uv sync
```

Then in your script or skill helper:

```python
from whatsapp_mcp_server import (
    search_contacts,
    list_messages,
    list_chats,
    get_chat,
    send_message,
    send_file,
    download_media,
)

# Search contacts and list chats (no MCP, no tokens)
contacts = search_contacts("alice")
chats = list_chats(limit=10)
for c in chats:
    print(c.name, c.jid)

# Read messages in a chat (returns formatted string)
messages = list_messages(chat_jid=chats[0].jid, limit=5)
print(messages)

# Send a message
ok, msg = send_message("1234567890", "Hello from Python")
```

All operations exposed as MCP tools are available this way: `search_contacts`, `list_messages`, `list_chats`, `get_chat`, `get_direct_chat_by_contact`, `get_contact_chats`, `get_last_interaction`, `get_message_context`, `get_reactions`, `send_message`, `send_file`, `send_audio_message`, `send_reaction`, `download_media`. Types like `Message`, `Chat`, `Contact`, `MessageContext`, `Reaction` are in `whatsapp_mcp_server` for type hints. Use this for token-heavy or fully automated workflows without an AI in the middle.

### MCP Tools

Claude can access the following tools to interact with WhatsApp:

- **search_contacts**: Search for contacts by name or phone number
- **list_messages**: Retrieve messages with optional filters and context
- **list_chats**: List available chats with metadata
- **get_chat**: Get information about a specific chat
- **get_direct_chat_by_contact**: Find a direct chat with a specific contact
- **get_contact_chats**: List all chats involving a specific contact
- **get_last_interaction**: Get the most recent message with a contact
- **get_message_context**: Retrieve context around a specific message
- **get_reactions**: Get all reactions (e.g. thumbs up, heart) on a message; returns reactor, emoji, and timestamp for each.
- **send_message**: Send a WhatsApp message to a specified phone number or group JID. Optional **reply_to_message_id** and **reply_to_sender_jid** send the message as a quote reply to a specific message.
- **send_reaction**: Send a reaction (emoji) to a message, or remove your reaction. For groups, pass **reply_to_sender_jid** (the sender of the message you're reacting to).
- **send_file**: Send a file (image, video, raw audio, document) to a specified recipient. Supports optional reply parameters.
- **send_audio_message**: Send an audio file as a WhatsApp voice message (requires the file to be an .ogg opus file or ffmpeg must be installed). Supports optional reply parameters.
- **download_media**: Download media from a WhatsApp message and get the local file path

### Reactions

You can read and send message reactions (e.g. 👍 ❤️ 😂):

- **get_reactions**: Pass `message_id` and `chat_jid` (from a message in `list_messages` or `get_message_context`) to get all reactions on that message. Returns a list of `reactor_sender`, `reaction_text` (emoji), and `timestamp`.
- **send_reaction**: Pass `chat_jid`, `message_id`, and `reaction` (emoji string, e.g. `"👍"` or `"❤️"`). Use empty string `""` to remove your reaction. For **group chats**, also pass `reply_to_sender_jid` (the `sender` of the message you're reacting to).

### Replying to a message

You can send a message as a **quote reply** to a specific message. When calling `send_message`, `send_file`, or `send_audio_message`, pass:

- **reply_to_message_id**: The `id` of the message you're replying to (from `list_messages` or `get_message_context`).
- **reply_to_sender_jid**: The `sender` JID of that message (so the quote shows the correct author; for groups this is the participant who sent the message).

Example: after getting a message from `list_messages`, use `message.id` and `message.sender` as the reply parameters.

### Media Handling Features

The MCP server supports both sending and receiving various media types:

#### Media Sending

You can send various media types to your WhatsApp contacts:

- **Images, Videos, Documents**: Use the `send_file` tool to share any supported media type.
- **Voice Messages**: Use the `send_audio_message` tool to send audio files as playable WhatsApp voice messages.
  - For optimal compatibility, audio files should be in `.ogg` Opus format.
  - With FFmpeg installed, the system will automatically convert other audio formats (MP3, WAV, etc.) to the required format.
  - Without FFmpeg, you can still send raw audio files using the `send_file` tool, but they won't appear as playable voice messages.

#### Media Downloading

By default, just the metadata of the media is stored in the local database. The message will indicate that media was sent. To access this media you need to use the download_media tool which takes the `message_id` and `chat_jid` (which are shown when printing messages containing the meda), this downloads the media and then returns the file path which can be then opened or passed to another tool.

## Development

### Secret scanning (Gitleaks)

[Gitleaks](https://github.com/gitleaks/gitleaks) runs in GitHub Actions on push and pull requests to `main`/`master`. To scan locally, install Gitleaks (e.g. `brew install gitleaks`) and run:

```bash
make gitleaks
```

To run Gitleaks automatically before each commit, install [pre-commit](https://pre-commit.com/) and enable the hook:

```bash
pip install pre-commit   # or: brew install pre-commit
pre-commit install
```

The hook scans staged changes only. To skip it for a single commit: `SKIP=gitleaks git commit -m "..."`.

## Technical Details

- The bridge REST API has **no authentication** and is intended for **localhost only**. Do not expose it to the network without additional protection (e.g. firewall, reverse proxy with auth).

Data flow:

1. Claude sends requests to the Python MCP server
2. The MCP server queries the Go bridge for WhatsApp data or directly to the SQLite database
3. The Go bridge accesses the WhatsApp API and keeps the SQLite database up to date
4. Data flows back through the chain to Claude
5. When sending messages, the request flows from Claude through the MCP server to the Go bridge and to WhatsApp

## Troubleshooting

- If you encounter permission issues when running uv, you may need to add it to your PATH or use the full path to the executable.
- Make sure both the Go application and the Python server are running for the integration to work properly.

### Authentication Issues

- **QR Code Not Displaying**: If the QR code doesn't appear, try restarting the authentication script. If issues persist, check if your terminal supports displaying QR codes.
- **WhatsApp Already Logged In**: If your session is already active, the Go bridge will automatically reconnect without showing a QR code.
- **Device Limit Reached**: WhatsApp limits the number of linked devices. If you reach this limit, you'll need to remove an existing device from WhatsApp on your phone (Settings > Linked Devices).
- **No Messages Loading**: After initial authentication, it can take several minutes for your message history to load, especially if you have many chats.
- **WhatsApp Out of Sync**: If your WhatsApp messages get out of sync with the bridge, delete both database files (`whatsapp-bridge/store/messages.db` and `whatsapp-bridge/store/whatsapp.db`) and restart the bridge to re-authenticate.

For additional Claude Desktop integration troubleshooting, see the [MCP documentation](https://modelcontextprotocol.io/quickstart/server#claude-for-desktop-integration-issues). The documentation includes helpful tips for checking logs and resolving common issues.
