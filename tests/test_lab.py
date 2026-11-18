import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from review_lab.agent import DATA
from review_lab.demo import DemoBackend
from review_lab.evaluate import run_suite
from review_lab.grading import judge_turn
from review_lab.openai_backend import OpenAIBackend, ProviderError


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.cases = json.loads((DATA / "cases.json").read_text(encoding="utf-8"))
        self.product = (DATA / "product.md").read_text(encoding="utf-8")
        self.prompt = (DATA / "agent-prompt.txt").read_text(encoding="utf-8")

    def run_demo(self, mode):
        return run_suite(
            self.cases, DemoBackend(), prompt=self.prompt, product=self.product,
            history_mode=mode, repeat=1,
        )

    def test_full_history_passes_code_checks_without_grading_rubrics(self):
        report = self.run_demo("full")
        self.assertEqual(report["summary"]["trials"], {"checks_only": 5})
        self.assertEqual(report["summary"]["checks"], {"pass": 15})
        self.assertEqual(report["summary"]["rubrics"], {"ungraded": 13})
        self.assertIsNone(report["summary"]["passing_all_trials"])

    def test_latest_message_control_breaks_turn_four_in_every_case(self):
        report = self.run_demo("latest")
        for case in report["results"]:
            with self.subTest(case=case["case"]):
                failures = [
                    turn["turn"]
                    for turn in case["turns"]
                    if any(score["status"] == "fail" for score in turn["checks"].values())
                ]
                self.assertEqual(failures, [4])
                self.assertEqual(case["status"], "fail")

    def test_paired_cases_change_only_first_user_message(self):
        positive, negative = self.run_demo("full")["results"][:2]
        self.assertEqual(
            [turn["user"] for turn in positive["turns"][1:]],
            [turn["user"] for turn in negative["turns"][1:]],
        )
        self.assertIn("Yes.", positive["turns"][3]["assistant"]["text"])
        self.assertIn("skip", negative["turns"][3]["assistant"]["text"])

    def test_live_shaped_run_replays_real_answers_and_judges_turn_prefix(self):
        client = Mock()

        def respond(**request):
            if "text" in request:
                payload = json.loads(request["input"][0]["content"])
                history = payload["transcript"]
                self.assertEqual(history[-1]["role"], "assistant")
                if "tailored_recommendation" in payload["criteria"]:
                    self.assertEqual(len(history), 8)
                scores = [
                    {"id": name, "passed": True, "reason": "Example", "evidence": history[-1]["content"]}
                    for name in payload["criteria"]
                ]
                return response(json.dumps({"scores": scores}), request["model"])
            if len(request["input"]) > 1:
                self.assertEqual(request["input"][1]["content"], "It is a plausible choice for pour-over.")
            reply = DemoBackend().generate(request["instructions"], request["input"])
            return response(reply.text, request["model"])

        client.responses.create.side_effect = respond
        report = run_suite(
            self.cases[:1], OpenAIBackend(client, "candidate"), prompt=self.prompt,
            product=self.product, history_mode="full", repeat=2,
            judge=OpenAIBackend(client, "judge"),
        )
        self.assertEqual(report["summary"]["trials"], {"pass": 2})
        self.assertEqual(report["summary"]["passing_all_trials"], 1)
        self.assertEqual(client.responses.create.call_count, 14)


class ResponsesTests(unittest.TestCase):
    def test_candidate_refusal_is_scored_as_reply(self):
        client = Mock()
        refusal = SimpleNamespace(type="refusal", refusal="I can't do that.")
        client.responses.create.return_value = response(
            "", "test", [SimpleNamespace(type="message", content=[refusal])]
        )
        backend = OpenAIBackend(client, "test")
        result = backend.generate("instructions", [{"role": "user", "content": "Question"}])
        self.assertEqual(result.text, refusal.refusal)
        self.assertEqual(result.usage, {"input_tokens": 10, "output_tokens": 5})
        self.assertFalse(client.responses.create.call_args.kwargs["store"])

    def test_judge_cannot_quote_a_different_turn(self):
        client = Mock()
        client.responses.create.return_value = response(
            '{"scores":[{"id":"policy","passed":true,"reason":"Relevant","evidence":"Earlier"}]}',
            "test",
        )
        history = [{"role": "user", "content": "Earlier"}, {"role": "assistant", "content": "Later"}]
        with self.assertRaisesRegex(ProviderError, "unverifiable evidence"):
            judge_turn(OpenAIBackend(client, "test"), "Sheet", history, {"policy": "Criterion"})

    def test_provider_error_is_distinct_and_does_not_copy_exception_body(self):
        client = Mock()
        error = RuntimeError("sensitive provider detail")
        error.status_code = 401
        client.responses.create.side_effect = error
        with self.assertRaisesRegex(ProviderError, r"^test: RuntimeError \(HTTP 401\)$"):
            OpenAIBackend(client, "test").generate("instructions", [])


def response(text, model, output=None):
    return SimpleNamespace(
        output_text=text,
        status="completed",
        output=output or [],
        model=model,
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )


if __name__ == "__main__":
    unittest.main()
