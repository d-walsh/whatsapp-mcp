#!/bin/bash
BRIDGE_DIR="$(dirname "$0")/whatsapp-bridge"
MCP_DIR="$(dirname "$0")/whatsapp-mcp-server"

# Use port 8081 to avoid conflict with Google MCP OAuth callback (port 8080)
export WHATSAPP_BRIDGE_PORT=8081
export WHATSAPP_API_BASE_URL="http://localhost:8081/api"

# Start bridge if not already running
if ! pgrep -f "whatsapp-bridge$" > /dev/null; then
    cd "$BRIDGE_DIR" && ./whatsapp-bridge > /dev/null 2>&1 &
    sleep 2  # Give bridge time to connect
fi

# Start the MCP server (this stays in foreground for stdio)
# Ensure uv is on PATH (see README Prerequisites)
cd "$MCP_DIR" && uv run main.py
