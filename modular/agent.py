# Core agent loop: parent orchestration with tool dispatch.

from prompts import SYSTEM
from tools import TOOL_HANDLERS, PARENT_TOOLS
from tools.subagent import handler as run_subagent


def agent_loop(client, model: str, messages: list):
    """Main loop: send messages to the model, dispatch tool calls, repeat until done."""
    while True:
        response = client.messages.create(
            model=model, system=SYSTEM, messages=messages,
            tools=PARENT_TOOLS, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})
        # No tool calls means the model is done responding
        if response.stop_reason != "tool_use":
            return
        results = []
        for block in response.content:
            if block.type == "tool_use":
                try:
                    # The subagent tool spawns a subagent; everything else runs directly
                    if block.name == "subagent":
                        desc = block.input.get("description", "subtask")
                        prompt = block.input.get("prompt", "")
                        print(f"> subagent ({desc}): {prompt[:80]}")
                        output = run_subagent(client, model, prompt)
                    else:
                        handler = TOOL_HANDLERS.get(block.name)
                        if not handler:
                            output = f"Error: Unknown tool '{block.name}'"
                        else:
                            output = handler(**block.input)
                except Exception as e:
                    output = f"Error: {type(e).__name__}: {e}"
                print(f"  {str(output)[:200]}")
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
        # Feed tool results back as a "user" message (Anthropic API convention)
        messages.append({"role": "user", "content": results})
