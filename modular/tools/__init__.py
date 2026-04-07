# Collects all tool schemas and handlers into the registries used by agent.py.
#
# CHILD_TOOLS  are the schemas available to subagents (no subagent -- prevents recursion).
# PARENT_TOOLS adds the subagent schema so only the parent can spawn subagents.

from pathlib import Path

from tools.bash import SCHEMA as bash_schema, handler as bash_handler
from tools.read_file import SCHEMA as read_schema, handler as read_handler
from tools.write_file import SCHEMA as write_schema, handler as write_handler
from tools.edit_file import SCHEMA as edit_schema, handler as edit_handler
from tools.subagent import SCHEMA as subagent_schema

CHILD_TOOLS = [bash_schema, read_schema, write_schema, edit_schema]
PARENT_TOOLS = CHILD_TOOLS + [subagent_schema]


def make_handlers(workdir: Path) -> dict:
    """Create tool handlers with workdir bound in."""
    return {
        "bash": lambda **kw: bash_handler(kw["command"], workdir),
        "read_file": lambda **kw: read_handler(kw["path"], workdir, kw.get("limit")),
        "write_file": lambda **kw: write_handler(kw["path"], kw["content"], workdir),
        "edit_file": lambda **kw: edit_handler(kw["path"], kw["old_text"], kw["new_text"], workdir),
    }
