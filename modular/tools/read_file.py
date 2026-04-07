# Tool: read_file -- read file contents with optional line limit.

from pathlib import Path

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


def _safe_path(p: str, workdir: Path) -> Path:
    path = (workdir / p).resolve()
    if not path.is_relative_to(workdir):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def handler(path: str, workdir: Path, limit: int = None) -> str:
    try:
        lines = _safe_path(path, workdir).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"
