# Lightweight logger for the agent loop.
# Three levels: default (round-by-round), --show-subagent, --trace (JSONL).

import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


class AgentLogger:
    def __init__(self, model: str, show_subagent=False, trace=False):
        self.show_subagent = show_subagent or trace
        self.trace = trace
        self._logfile = None
        # Per-turn state
        self._round = 0
        self._tool_counts = Counter()
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._turn_start = None
        # Sub-agent state
        self._sub_round = 0
        self._sub_tool_counts = Counter()
        self._sub_input_tokens = 0
        self._sub_output_tokens = 0

        print(f"Model: {model}")
        if trace:
            self._ensure_logfile()
            print(f"[Logging to {self._logpath}]")

    # --- Turn lifecycle ---

    def turn_start(self):
        self._round = 0
        self._tool_counts.clear()
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._turn_start = time.monotonic()

    def turn_end(self):
        elapsed = time.monotonic() - self._turn_start if self._turn_start else 0
        parts = [f"{self._round} round{'s' if self._round != 1 else ''}"]
        if self._tool_counts:
            parts.append(self._format_tool_summary(self._tool_counts))
        parts.append(self._format_tokens(self._total_input_tokens, self._total_output_tokens))
        parts.append(f"{elapsed:.1f}s")
        print(f"[{' | '.join(parts)}]")
        if self.trace:
            self._write_jsonl({
                "type": "turn_summary",
                "rounds": self._round,
                "tool_counts": dict(self._tool_counts),
                "tokens": {"input": self._total_input_tokens, "output": self._total_output_tokens},
                "elapsed": round(elapsed, 2),
            })

    # --- Parent round tracking ---

    def round_start(self, tool_names: list[str]):
        self._round += 1
        self._tool_counts.update(tool_names)
        print(f"--- Round {self._round} ---")
        print(f"  Tools: {', '.join(tool_names)}")

    def round_response(self, response):
        usage = getattr(response, "usage", None)
        if usage:
            self._total_input_tokens += getattr(usage, "input_tokens", 0)
            self._total_output_tokens += getattr(usage, "output_tokens", 0)
        if self.trace:
            self._write_jsonl({
                "type": "response",
                "agent": "parent",
                "round": self._round,
                "content": _serialize_content(response.content),
                "stop_reason": response.stop_reason,
                "usage": _serialize_usage(usage),
            })

    def log_request(self, agent_label: str, round_num: int, messages: list,
                    system: str, tools: list, model: str):
        if not self.trace:
            return
        self._write_jsonl({
            "type": "request",
            "agent": agent_label,
            "round": round_num,
            "model": model,
            "system": system,
            "messages": _serialize_messages(messages),
            "tools": tools,
        })

    # --- Subagent tracking ---

    def subagent_start(self, description: str):
        self._sub_round = 0
        self._sub_tool_counts.clear()
        self._sub_input_tokens = 0
        self._sub_output_tokens = 0

    def subagent_round_start(self, tool_names: list[str]):
        self._sub_round += 1
        self._sub_tool_counts.update(tool_names)
        if self.show_subagent:
            print(f"  | --- Sub-round {self._sub_round} ---")
            print(f"  |   Tools: {', '.join(tool_names)}")

    def subagent_round_response(self, response):
        usage = getattr(response, "usage", None)
        if usage:
            self._sub_input_tokens += getattr(usage, "input_tokens", 0)
            self._sub_output_tokens += getattr(usage, "output_tokens", 0)
        if self.trace:
            self._write_jsonl({
                "type": "response",
                "agent": "subagent",
                "round": self._sub_round,
                "content": _serialize_content(response.content),
                "stop_reason": response.stop_reason,
                "usage": _serialize_usage(usage),
            })

    def subagent_end(self):
        if self.show_subagent:
            parts = [f"{self._sub_round} sub-round{'s' if self._sub_round != 1 else ''}"]
            if self._sub_tool_counts:
                parts.append(self._format_tool_summary(self._sub_tool_counts))
            parts.append(self._format_tokens(self._sub_input_tokens, self._sub_output_tokens))
            print(f"  | [{' | '.join(parts)}]")
        # Fold subagent tokens into parent totals
        self._total_input_tokens += self._sub_input_tokens
        self._total_output_tokens += self._sub_output_tokens

    # --- JSONL file management ---

    def _ensure_logfile(self):
        if self._logfile:
            return
        logdir = Path(".agent_logs")
        logdir.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._logpath = logdir / f"agent_log_{stamp}.jsonl"
        self._logfile = open(self._logpath, "a", encoding="utf-8")

    def _write_jsonl(self, record: dict):
        self._ensure_logfile()
        record["ts"] = datetime.now(timezone.utc).isoformat()
        self._logfile.write(json.dumps(record, default=str) + "\n")
        self._logfile.flush()

    # --- Formatting helpers ---

    @staticmethod
    def _format_tool_summary(counts: Counter) -> str:
        return ", ".join(f"{name} x{n}" for name, n in counts.most_common())

    @staticmethod
    def _format_tokens(inp: int, out: int) -> str:
        def _fmt(n):
            return f"{n / 1000:.1f}k" if n >= 1000 else str(n)
        return f"{_fmt(inp)} in / {_fmt(out)} out"


# --- Serialization helpers (module-level) ---

def _serialize_content(content):
    """Convert response content blocks to JSON-serializable dicts."""
    if not isinstance(content, list):
        return content
    result = []
    for block in content:
        if hasattr(block, "model_dump"):
            result.append(block.model_dump())
        elif hasattr(block, "__dict__"):
            result.append(vars(block))
        else:
            result.append(str(block))
    return result


def _serialize_usage(usage):
    if usage is None:
        return None
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if hasattr(usage, "__dict__"):
        return vars(usage)
    return str(usage)


def _serialize_messages(messages):
    """Deep-serialize a messages list for JSONL output."""
    result = []
    for msg in messages:
        content = msg.get("content", msg.get("content"))
        if isinstance(content, list):
            serialized_content = []
            for item in content:
                if hasattr(item, "model_dump"):
                    serialized_content.append(item.model_dump())
                elif hasattr(item, "__dict__"):
                    serialized_content.append(vars(item))
                elif isinstance(item, dict):
                    serialized_content.append(item)
                else:
                    serialized_content.append(str(item))
            result.append({"role": msg["role"], "content": serialized_content})
        else:
            result.append(msg)
    return result
