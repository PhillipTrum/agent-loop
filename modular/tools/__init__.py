# Collects all tool schemas and handlers into the registries used by agent.py.
#
# TOOL_HANDLERS maps tool name -> callable for execution.
# CHILD_TOOLS  are the schemas available to subagents (no subagent -- prevents recursion).
# PARENT_TOOLS adds the subagent schema so only the parent can spawn subagents.

from tools.bash import SCHEMA as bash_schema, handler as bash_handler
from tools.read_file import SCHEMA as read_schema, handler as read_handler
from tools.write_file import SCHEMA as write_schema, handler as write_handler
from tools.edit_file import SCHEMA as edit_schema, handler as edit_handler
from tools.subagent import SCHEMA as subagent_schema

# Lambdas unpack the model's keyword dict into positional handler args
TOOL_HANDLERS = {
    "bash": lambda **kw: bash_handler(kw["command"]),
    "read_file": lambda **kw: read_handler(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: write_handler(kw["path"], kw["content"]),
    "edit_file": lambda **kw: edit_handler(kw["path"], kw["old_text"], kw["new_text"]),
}

CHILD_TOOLS = [bash_schema, read_schema, write_schema, edit_schema]
PARENT_TOOLS = CHILD_TOOLS + [subagent_schema]
