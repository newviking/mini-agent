from __future__ import annotations

import argparse

from agent.runtime import AgentRuntime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the mini local Agent Runtime CLI.")
    parser.add_argument("--session", default="default", help="Session id to load and persist.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        runtime = AgentRuntime()
    except RuntimeError as exc:
        print(f"Configuration error: {exc}")
        return

    print(f"mini-runtime-agent session={args.session}")
    print("Type exit or quit to stop.")

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        answer = runtime.run_turn(user_input, session_id=args.session)
        print(answer)


if __name__ == "__main__":
    main()
