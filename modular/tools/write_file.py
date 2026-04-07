# Tool: write_file -- create or overwrite a file.

from pathlib import Path

SCHEMA = {
    "name": "write_file",
    "description": "Write content to file.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    },
}


def _safe_path(p: str, workdir: Path) -> Path:
    path = (workdir / p).resolve()
    if not path.is_relative_to(workdir):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def handler(path: str, content: str, workdir: Path) -> str:
    try:
        fp = _safe_path(path, workdir)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes"
    except Exception as e:
        return f"Error: {e}"
