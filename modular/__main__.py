# CLI entry point: parses provider/model args, then runs the REPL.

import argparse

from models import create_client
from agent import agent_loop


def main():
    parser = argparse.ArgumentParser(description="Coding agent REPL")
    parser.add_argument("--provider", default="anthropic", help="LLM provider (default: anthropic)")
    parser.add_argument("--model", default=None, help="Model ID (default: MODEL_ID env var)")
    parser.add_argument("--base-url", default=None, help="Custom API base URL (e.g. for local LLMs)")
    args = parser.parse_args()

    import os
    model = args.model or os.environ["MODEL_ID"]
    client, model = create_client(args.provider, model, base_url=args.base_url)

    history = []  # conversation history shared across turns
    while True:
        try:
            query = input("\033[36ms04 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(client, model, history)
        # Print the model's final text response
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()


if __name__ == "__main__":
    main()
