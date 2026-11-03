"""A tiny stdio MCP server used by the tests."""

import json
import sys

TOOLS = [
    {
        "name": "echo",
        "description": "Echo text back.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {"name": "explode", "description": "Always fails.", "inputSchema": {"type": "object"}},
    {"name": "snap", "description": "Returns an image.", "inputSchema": {"type": "object"}},
]


def reply(message_id, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": message_id, "result": result}) + "\n")
    sys.stdout.flush()


print("this server logs a non-JSON banner to stdout", flush=True)
for line in sys.stdin:
    message = json.loads(line)
    method = message.get("method")
    if "id" not in message:
        continue
    if method == "initialize":
        reply(
            message["id"],
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fake", "version": "1"},
            },
        )
    elif method == "tools/list":
        reply(message["id"], {"tools": TOOLS})
    elif method == "tools/call":
        params = message["params"]
        if params["name"] == "echo":
            reply(
                message["id"], {"content": [{"type": "text", "text": params["arguments"]["text"]}]}
            )
        elif params["name"] == "snap":
            image = {"type": "image", "data": "iVBORw0KGgo=", "mimeType": "image/png"}
            reply(message["id"], {"content": [{"type": "text", "text": "shot"}, image]})
        else:
            reply(message["id"], {"content": [{"type": "text", "text": "boom"}], "isError": True})
