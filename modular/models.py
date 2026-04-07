# Model and provider selection.
# The CLI chooses a provider and model, and this module returns a
# client that exposes a uniform interface regardless of provider.

import json
import os
from types import SimpleNamespace

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
        create_fn = MESSAGE_CREATORS.get(self.provider)
        if not create_fn:
            raise ValueError(f"Unknown provider: {self.provider}")
        return create_fn(
            self.raw,
            model=model,
            system=system,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
        )


def _anthropic_create(raw_client, *, model, system, messages, tools, max_tokens):
    return raw_client.messages.create(
        model=model,
        system=system,
        messages=messages,
        tools=tools,
        max_tokens=max_tokens,
    )


def _openai_create(raw_client, *, model, system, messages, tools, max_tokens):
    """Translate Anthropic-style calls to OpenAI's chat completions API."""
    response = raw_client.chat.completions.create(
        model=model,
        messages=_to_openai_messages(system, messages),
        tools=_to_openai_tools(tools) if tools else None,
        max_tokens=max_tokens,
    )
    return _from_openai_response(response)


def _to_openai_messages(system, messages):
    oai_messages = [{"role": "system", "content": system}]
    for msg in messages:
        if msg["role"] == "user":
            if isinstance(msg["content"], list):
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
            oai_messages.append(_to_openai_assistant_message(msg["content"]))
    return oai_messages


def _to_openai_assistant_message(content):
    oai_msg = {"role": "assistant", "content": None}
    tool_calls = []
    text_parts = []

    if isinstance(content, list):
        for block in content:
            if not hasattr(block, "type"):
                continue
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
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
    return oai_msg


def _to_openai_tools(tools):
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        }
        for tool in tools
    ]


def _from_openai_response(response):
    choice = response.choices[0]
    content_blocks = []

    if choice.message.content:
        content_blocks.append(SimpleNamespace(type="text", text=choice.message.content))

    if choice.message.tool_calls:
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
    factory = CLIENT_FACTORIES.get(provider)
    if not factory:
        raise ValueError(f"Unknown provider: {provider}")
    return factory(model, base_url)


def _create_anthropic_client(model: str, base_url: str = None):
    from anthropic import Anthropic

    url = base_url or os.getenv("ANTHROPIC_BASE_URL")
    raw = Anthropic(base_url=url)
    return UnifiedClient("anthropic", raw), model


def _create_openai_client(model: str, base_url: str = None):
    from openai import OpenAI

    # CLI --base-url overrides the OPENAI_BASE_URL env var
    raw = OpenAI(base_url=base_url) if base_url else OpenAI()
    return UnifiedClient("openai", raw), model


MESSAGE_CREATORS = {
    "anthropic": _anthropic_create,
    "openai": _openai_create,
}


CLIENT_FACTORIES = {
    "anthropic": _create_anthropic_client,
    "openai": _create_openai_client,
}
