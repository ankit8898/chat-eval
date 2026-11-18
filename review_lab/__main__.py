"""Run a chat session or a reproducible eval from the terminal."""

import argparse
import json
import os
import sys
from pathlib import Path

from .agent import DATA, DEFAULT_MODEL, Chat, instructions
from .demo import DemoBackend
from .evaluate import run_suite
from .openai_backend import OpenAIBackend, ProviderError


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    for name in ("chat", "eval"):
        command = commands.add_parser(name)
        command.add_argument("--backend", choices=("demo", "openai"), default="demo")
        command.add_argument("--model", default=os.getenv("OPENAI_MODEL", DEFAULT_MODEL))
        command.add_argument("--history", choices=("full", "latest"), default="full")
        command.add_argument("--prompt", type=Path, default=DATA / "agent-prompt.txt")
    evaluation = commands.choices["eval"]
    evaluation.add_argument("--suite", type=Path, default=DATA / "cases.json")
    evaluation.add_argument("--case", action="append", help="Only run this case ID. Repeat to select several.")
    evaluation.add_argument("--repeat", type=int, default=1)
    evaluation.add_argument("--judge-model", default=os.getenv("OPENAI_JUDGE_MODEL", "gpt-6.2-astra"))
    evaluation.add_argument("--checks-only", action="store_true", help="Skip the live semantic judge.")
    evaluation.add_argument("--output", type=Path, default=Path("reports/latest.json"))
    return cli


def print_report(report: dict) -> None:
    for case in report["results"]:
        print(f"{case['status'].upper():12} {case['case']} (trial {case['trial']})")
        for turn in case["turns"]:
            for key in ("agent_error", "judge_error"):
                if key in turn:
                    print(f"  Turn {turn['turn']}: {turn[key]}")
            for group in ("checks", "rubrics"):
                for name, score in turn[group].items():
                    if score["status"] == "fail":
                        reason = score.get("reason") or f"No match for {score['pattern']!r}"
                        print(f"  Turn {turn['turn']} {name}: {reason}")
    summary = report["summary"]
    print(f"Code checks: {summary['checks']}")
    print(f"Rubrics: {summary['rubrics']}")
    print(f"Scenario trials: {summary['trials']}")
    if summary["passing_all_trials"] is not None:
        print(f"Cases passing every trial: {summary['passing_all_trials']}/{summary['cases']}")


def main() -> int:
    cli = parser()
    args = cli.parse_args()
    if args.command == "eval" and args.repeat < 1:
        cli.error("--repeat must be at least 1")

    prompt = args.prompt.read_text(encoding="utf-8")
    product = (DATA / "product.md").read_text(encoding="utf-8")
    backend = DemoBackend()
    judge = None
    if args.backend == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            cli.error("Set OPENAI_API_KEY in your shell for the OpenAI backend.")
        try:
            from openai import OpenAI
        except ImportError:
            cli.error("Install the live dependency with python -m pip install -r requirements.txt.")
        client = OpenAI(timeout=90.0, max_retries=2)
        backend = OpenAIBackend(client, args.model)
        if args.command == "eval" and not args.checks_only:
            judge = OpenAIBackend(client, args.judge_model)

    if args.command == "chat":
        chat = Chat(backend, instructions(prompt, product), args.history)
        print(f"Ridge Mill 24 review chat ({args.backend}, history={args.history}). Type /quit to exit.")
        while True:
            try:
                message = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                return 0
            if message == "/quit":
                return 0
            if message:
                try:
                    print(f"Agent: {chat.reply(message).text}")
                except ProviderError as exc:
                    print(f"Request failed: {exc}", file=sys.stderr)
                    return 2

    cases = json.loads(args.suite.read_text(encoding="utf-8"))
    if args.case:
        missing = set(args.case) - {case["id"] for case in cases}
        if missing:
            cli.error(f"unknown case IDs: {', '.join(sorted(missing))}")
        cases = [case for case in cases if case["id"] in args.case]
    if not cases:
        cli.error("the suite must contain at least one case")
    report = run_suite(
        cases, backend, prompt=prompt, product=product, history_mode=args.history,
        repeat=args.repeat, judge=judge,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print_report(report)
    print(f"Transcript and scores: {args.output}")
    trials = report["summary"]["trials"]
    if trials.get("error"):
        return 2
    return int(bool(trials.get("fail")))


if __name__ == "__main__":
    sys.exit(main())
