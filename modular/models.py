# Model and provider selection.
# The CLI chooses a provider and model, and this module returns a
# client that exposes a uniform interface regardless of provider.

import os

from dotenv import load_dotenv

load_dotenv(override=True)


class UnifiedClient:
    """Wraps different provider SDKs behind a common messages.create() interface.

    This lets agent.py call client.messages.create() with the same arguments
    regardless of whether the backend is Anthropic or OpenAI.
    """

    def __init__(self, provider, raw_client):
        self.provider = provider
        self.raw = raw_client
        self.messages = self  # so client.messages.create() works

    def create(self, *, model, system, messages, tools, max_tokens):
        if self.provider == "anthropic":
            return self.raw.messages.create(
                model=model, system=system, messages=messages,
                tools=tools, max_tokens=max_tokens,
            )

        if self.provider == "openai":
            return self._openai_create(
                model=model, system=system, messages=messages,
                tools=tools, max_tokens=max_tokens,
            )

    def _openai_create(self, *, model, system, messages, tools, max_tokens):
        """Translate Anthropic-style calls to OpenAI's chat completions API,
        then wrap the response to match the Anthropic response shape."""
        from types import SimpleNamespace

        # Build OpenAI message list
        oai_messages = [{"role": "system", "content": system}]
        for msg in messages:
            if msg["role"] == "user":
                # Could be a string prompt or a list of tool_result dicts
                if isinstance(msg["content"], list):
                    # Tool results -> OpenAI tool messages
                    for item in msg["content"]:
                        if item.get("type") == "tool_result":
                            oai_messages.append({
                                "role": "tool",
                                "tool_call_id": item["tool_use_id"],
                                "content": item["content"],
                            })
                else:
                    oai_messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                # Convert Anthropic content blocks to OpenAI format
                oai_msg = {"role": "assistant", "content": None}
                tool_calls = []
                text_parts = []
                content = msg["content"]
                if isinstance(content, list):
                    for block in content:
                        if hasattr(block, "type"):
                            if block.type == "text":
                                text_parts.append(block.text)
                            elif block.type == "tool_use":
                                import json
                                tool_calls.append({
                                    "id": block.id,
                                    "type": "function",
                                    "function": {
                                        "name": block.name,
                                        "arguments": json.dumps(block.input),
                                    },
                                })
                if text_parts:
                    oai_msg["content"] = "\n".join(text_parts)
                if tool_calls:
                    oai_msg["tool_calls"] = tool_calls
                oai_messages.append(oai_msg)

        # Convert Anthropic tool schemas to OpenAI function format
        oai_tools = []
        for tool in tools:
            oai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            })

        response = self.raw.chat.completions.create(
            model=model,
            messages=oai_messages,
            tools=oai_tools if oai_tools else None,
            max_tokens=max_tokens,
        )

        # Wrap OpenAI response to look like an Anthropic response
        choice = response.choices[0]
        content_blocks = []

        if choice.message.content:
            content_blocks.append(SimpleNamespace(type="text", text=choice.message.content))

        if choice.message.tool_calls:
            import json
            for tc in choice.message.tool_calls:
                content_blocks.append(SimpleNamespace(
                    type="tool_use",
                    id=tc.id,
                    name=tc.function.name,
                    input=json.loads(tc.function.arguments),
                ))

        stop_reason = "tool_use" if choice.message.tool_calls else "end_turn"
        return SimpleNamespace(content=content_blocks, stop_reason=stop_reason)


def create_client(provider: str, model: str, base_url: str = None):
    """Return (UnifiedClient, model_id) for the given provider."""
    if provider == "anthropic":
        from anthropic import Anthropic

        url = base_url or os.getenv("ANTHROPIC_BASE_URL")
        if url:
            os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

        raw = Anthropic(base_url=url)
        return UnifiedClient("anthropic", raw), model

    if provider == "openai":
        from openai import OpenAI

        # CLI --base-url overrides the OPENAI_BASE_URL env var
        raw = OpenAI(base_url=base_url) if base_url else OpenAI()
        return UnifiedClient("openai", raw), model

    raise ValueError(f"Unknown provider: {provider}")
