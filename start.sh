#!/bin/bash
BRIDGE_DIR="$(dirname "$0")/whatsapp-bridge"
MCP_DIR="$(dirname "$0")/whatsapp-mcp-server"

# Start bridge if not already running
if ! pgrep -f "whatsapp-bridge$" > /dev/null; then
    cd "$BRIDGE_DIR" && ./whatsapp-bridge > /dev/null 2>&1 &
    sleep 2  # Give bridge time to connect
fi

# Start the MCP server (this stays in foreground for stdio)
cd "$MCP_DIR" && /Users/david/.local/bin/uv run main.py
