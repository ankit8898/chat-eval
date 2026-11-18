"""Replay scripted users through the real chat path and retain a diagnostic trace."""

import hashlib
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Literal

from .agent import Backend, Chat, instructions
from .grading import JUDGE_PROMPT, judge_turn, string_checks
from .openai_backend import OpenAIBackend, ProviderError


def run_suite(
    cases: list[dict],
    backend: Backend,
    *,
    prompt: str,
    product: str,
    history_mode: Literal["full", "latest"],
    repeat: int,
    judge: OpenAIBackend | None = None,
) -> dict:
    results = []
    checks = Counter()
    rubrics = Counter()
    for case in cases:
        for trial in range(1, repeat + 1):
            chat = Chat(backend, instructions(prompt, product), history_mode)
            result = {"case": case["id"], "purpose": case["purpose"], "trial": trial, "turns": []}
            results.append(result)
            for index, turn in enumerate(case["turns"], 1):
                row = {"turn": index, "user": turn["user"], "checks": {}, "rubrics": {}}
                result["turns"].append(row)
                criteria = turn.get("rubric", {})
                try:
                    reply = chat.reply(turn["user"])
                except ProviderError as exc:
                    row["agent_error"] = str(exc)
                    break
                row["assistant"] = asdict(reply)
                row["checks"] = string_checks(turn.get("match", {}), reply.text)
                if criteria:
                    row["rubrics"] = {
                        name: {"status": "ungraded", "criterion": criterion}
                        for name, criterion in criteria.items()
                    }
                    if judge is not None:
                        try:
                            row["rubrics"], row["judge"] = judge_turn(judge, product, chat.history, criteria)
                        except ProviderError as exc:
                            row["judge_error"] = str(exc)
                checks.update(score["status"] for score in row["checks"].values())
                rubrics.update(score["status"] for score in row["rubrics"].values())

            turns = result["turns"]
            statuses = {
                score["status"] for row in turns for group in ("checks", "rubrics") for score in row[group].values()
            }
            if any("agent_error" in row or "judge_error" in row for row in turns):
                result["status"] = "error"
            elif "fail" in statuses:
                result["status"] = "fail"
            elif "ungraded" in statuses:
                result["status"] = "checks_only"
            else:
                result["status"] = "pass"
    return {
        "started_with": {
            "history": history_mode,
            "repeat": repeat,
            "agent": getattr(backend, "model", "scripted-demo"),
            "judge": judge.model if judge else None,
            "hashes": {
                name: hashlib.sha256(value.encode()).hexdigest()
                for name, value in {
                    "agent_prompt": prompt,
                    "product_sheet": product,
                    "cases": json.dumps(cases, sort_keys=True),
                    "judge_prompt": JUDGE_PROMPT,
                }.items()
            },
        },
        "reported_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "trials": dict(Counter(case["status"] for case in results)),
            "checks": dict(checks),
            "rubrics": dict(rubrics),
            "passing_all_trials": (
                sum(all(run["status"] == "pass" for run in results if run["case"] == case["id"]) for case in cases)
                if judge
                else None
            ),
            "cases": len(cases),
        },
        "results": results,
    }
