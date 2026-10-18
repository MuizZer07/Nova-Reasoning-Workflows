#!/usr/bin/env python3
"""A minimal command-line chat with the Nova workflows over one dataset.

    python scripts/nova_cli/cli.py --dataset GSE47363 --workflow auto
    python scripts/nova_cli/cli.py --dataset GSE47363 --session 3fa2c1d0      # resume a session

Commands inside the chat:
    /workflow instant|thinking|deep_thinking|auto     switch workflow (the session and its history are kept)
    /history                                          show the conversation so far
    /sessions                                         list saved sessions for this dataset
    /quit

This is an illustrative sketch of how Nova is put together (prompts, tools, sessions); it needs an
OpenAI-compatible model endpoint configured through environment variables (see llm.py).
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm import LLM  # noqa: E402
from session import Session  # noqa: E402
from tools import ExperimentTools  # noqa: E402
from workflows import WORKFLOWS  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", required=True, help="GEO accession, e.g. GSE47363")
    ap.add_argument("--workflow", default="auto", choices=list(WORKFLOWS))
    ap.add_argument("--session", help="id of a saved session to resume")
    args = ap.parse_args()

    tools = ExperimentTools(args.dataset)
    session = Session.load(args.dataset, args.session) if args.session else Session(args.dataset, args.workflow)
    llm = LLM()
    info = tools.get_experiment_info()
    print(f"Nova · {info['experiment']} ({info['contrast']}) · session {session.id} · workflow {session.workflow}")

    while True:
        try:
            query = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not query:
            continue
        if query == "/quit":
            break
        if query.startswith("/workflow"):
            choice = query.split()[-1]
            if choice in WORKFLOWS:
                session.workflow = choice
                session.save()
            print(f"workflow: {session.workflow}")
            continue
        if query == "/history":
            for m in session.messages:
                print(f"[{m['role']}{'/' + m['workflow'] if m.get('workflow') else ''}] {m['content'][:300]}")
            continue
        if query == "/sessions":
            print("\n".join(Session.list(args.dataset)) or "(none)")
            continue

        answer, log = WORKFLOWS[session.workflow](llm, tools, session.history(), query)
        session.add("user", query)
        session.add("assistant", answer, workflow=session.workflow, tool_calls=len(log))
        print(f"\nnova ({session.workflow}, {len(log)} tool calls)> {answer}")


if __name__ == "__main__":
    main()
