"""Консольный вход для вопросов агенту."""

import argparse
import json

from source.agent.dependencies import get_agent_tools
from source.agent.routerai import MODEL, RouterAIAgent


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask the reconciliation agent")
    parser.add_argument("question", help="Question in Russian with a month in YYYY-MM format")
    parser.add_argument("--json", action="store_true", help="Include tool evidence, without secrets")
    args = parser.parse_args()
    agent = RouterAIAgent.from_env(get_agent_tools())
    answer = agent.ask(args.question)
    if args.json:
        print(json.dumps({"question": args.question, "model": MODEL,
                          "tool_calls": agent.trace, "answer": answer},
                         ensure_ascii=False, indent=2))
    else:
        print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
