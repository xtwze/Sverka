"""Консольный вход для вопросов агенту."""

import argparse

from source.agent.dependencies import get_agent_tools
from source.agent.routerai import RouterAIAgent


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask the reconciliation agent")
    parser.add_argument("question", help="Question in Russian with a month in YYYY-MM format")
    args = parser.parse_args()
    print(RouterAIAgent.from_env(get_agent_tools()).ask(args.question))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
