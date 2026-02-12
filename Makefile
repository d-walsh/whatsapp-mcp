.PHONY: run-bridge run-server install-server test

run-bridge:
	cd whatsapp-bridge && go run main.go

run-server:
	cd whatsapp-mcp-server && uv run main.py

install-server:
	cd whatsapp-mcp-server && uv sync

test:
	cd whatsapp-mcp-server && uv sync --extra dev && uv run pytest tests/ -v
