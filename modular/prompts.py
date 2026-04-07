# System prompts for the parent agent and subagents.

from workspace import WORKDIR

# Parent agent can delegate via the subagent tool; subagent cannot (no recursion).
SYSTEM = f"You are a coding agent at {WORKDIR}. Use the subagent tool to delegate exploration or subtasks."
SUBAGENT_SYSTEM = f"You are a coding subagent at {WORKDIR}. Complete the given task, then summarize your findings."
