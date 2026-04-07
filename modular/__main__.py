# CLI entry point: parses provider/model args, then runs the REPL.

import argparse

from models import create_client
from agent import agent_loop
from agent_logging import AgentLogger


def main():
    parser = argparse.ArgumentParser(description="Coding agent REPL")
    parser.add_argument("--provider", default="anthropic", help="LLM provider (default: anthropic)")
    parser.add_argument("--model", default=None, help="Model ID")
    parser.add_argument("--base-url", default=None, help="Custom API base URL (e.g. for local or self-hosted LLMs)")
    parser.add_argument("--show-subagent", action="store_true", help="Show round-by-round subagent activity")
    parser.add_argument("--trace", action="store_true", help="Log full prompts and responses to JSONL file")
    args = parser.parse_args()

    model = args.model
    if not model:
        parser.error("--model is required")
    client, model = create_client(args.provider, model, base_url=args.base_url)
    logger = AgentLogger(model=model, show_subagent=args.show_subagent, trace=args.trace)

    history = []  # conversation history shared across turns
    while True:
        try:
            query = input("\033[36m>>> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        # Main agent loop: send messages to the model, dispatch tool calls, repeat until done
        logger.turn_start()
        agent_loop(client, model, history, logger=logger)
        logger.turn_end()
        # Print the model's final text response
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()


if __name__ == "__main__":
    main()
