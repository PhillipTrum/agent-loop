# Tool: read_file -- read file contents with optional line limit.

from workspace import safe_path

SCHEMA = {
    "name": "read_file",
    "description": "Read file contents.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "limit": {"type": "integer"},
        },
        "required": ["path"],
    },
}


def handler(path: str, limit: int = None) -> str:
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"
