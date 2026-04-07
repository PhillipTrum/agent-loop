# Tool: subagent -- spawn a subagent with fresh context.
# Uses a late import for make_handlers/CHILD_TOOLS to avoid a circular
# dependency with tools/__init__.py.

from pathlib import Path

from prompts import SUBAGENT_SYSTEM

SCHEMA = {
    "name": "subagent",
    "description": "Spawn a subagent with fresh context. It shares the filesystem but not conversation history.",
    "input_schema": {
        "type": "object",
        "properties": {
            "prompt": {"type": "string"},
            "description": {"type": "string", "description": "Short description of the subagent's task"},
        },
        "required": ["prompt"],
    },
}


def handler(client, model: str, prompt: str, workdir: Path, logger=None) -> str:
    """Run a child agent with fresh context. Returns only its final text summary."""
    from tools import make_handlers, CHILD_TOOLS

    system = SUBAGENT_SYSTEM.format(workdir=workdir)
    tool_handlers = make_handlers(workdir)

    if logger:
        logger.subagent_start(prompt[:60])

    sub_messages = [{"role": "user", "content": prompt}]
    for _ in range(30):  # safety cap on tool-use rounds
        if logger:
            logger.log_request("subagent", logger._sub_round + 1, sub_messages,
                               system, CHILD_TOOLS, model)
        response = client.messages.create(
            model=model, system=system, messages=sub_messages,
            tools=CHILD_TOOLS, max_tokens=8000,
        )
        sub_messages.append({"role": "assistant", "content": response.content})
        if logger:
            logger.subagent_round_response(response)
        if response.stop_reason != "tool_use":
            break
        # Log this round's tool calls
        tool_names = [b.name for b in response.content if b.type == "tool_use"]
        if logger:
            logger.subagent_round_start(tool_names)
        # Execute every tool the model requested and collect results
        results = []
        for block in response.content:
            if block.type == "tool_use":
                try:
                    tool_handler = tool_handlers.get(block.name)
                    if not tool_handler:
                        output = f"Error: Unknown tool '{block.name}'"
                    else:
                        output = tool_handler(**block.input)
                except Exception as e:
                    output = f"Error: {type(e).__name__}: {e}"
                if logger:
                    logger.subagent_tool_output(block, output)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)[:50000]})
        sub_messages.append({"role": "user", "content": results})

    if logger:
        logger.subagent_end()
    # Only the final text goes back to the parent -- child context is discarded
    return "".join(b.text for b in response.content if hasattr(b, "text")) or "(no summary)"
