# Product Review Chat Evals

A hands-on lab for testing a chat agent across five-turn conversations. You can chat with GPT-6.2 Sol about the fictional Ridge Mill 24 coffee grinder, replay a fixed evaluation suite, and deliberately break conversation history to see which checks catch the regression.

## 1. Run the lab offline

From the repository root with Python 3.11 or newer:

```bash
python -m review_lab eval --output reports/full.json
python -m review_lab eval --history latest --output reports/latest-only.json
```

The second command intentionally exits with status 1. Open both JSON reports and compare turn four.

| Scripted run | Code checks passed | Semantic criteria graded | Scenarios with failed checks |
| --- | ---: | ---: | ---: |
| Full history | 15 / 15 | 0 / 13 | 0 / 5 |
| Latest user message only | 8 / 15 | 0 / 13 | 5 / 5 |

The scripted demo proves that the replay and scoring harness can detect a known history bug. The live run measures model behavior.

## 2. Play a conversation

Start the keyless demo with `python -m review_lab chat`. Enter these five messages one at a time:

1. I mostly brew pour-over using paper filters. I'm considering the Ridge Mill 24.
2. How many grind settings does it have?
3. How much does it cost?
4. Given how I brew, would you recommend it for me?
5. What's one drawback to mention in my review?

Type `/quit` to exit. Start a fresh chat and change the first message to *I mostly brew espresso using an unpressurized basket. I'm considering the Ridge Mill 24.* Keep questions two through five the same. The recommendation should change on turn four.

## 3. Run GPT-6.2 Sol

Install the OpenAI SDK in a virtual environment and set `OPENAI_API_KEY` in your shell.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

python -m review_lab chat --backend openai

python -m review_lab eval --backend openai \
  --case pour-over --case espresso \
  --output reports/live-pair.json
```

The candidate defaults to `gpt-6.2-sol` and the independent rubric call defaults to `gpt-6.2-astra`. Override them with `--model` and `--judge-model` or their respective environment variables `OPENAI_MODEL` and `OPENAI_JUDGE_MODEL`. Add `--checks-only` to skip judge calls. With no case filter, the bundled suite makes 25 candidate calls and 13 judge calls per repeat, before retries. API usage is billable. [GPT-6.2 Sol model documentation](https://developers.openai.com/api/docs/models/gpt-6.2-sol)

## What the five conversations test

| Case | What turn four should retrieve | Other behavior |
| --- | --- | --- |
| `pour-over` | The turn-one brewing method | Recommend the grinder for pour-over and give a fair drawback |
| `espresso` | The turn-one brewing method | Advise against it for an unpressurized basket |
| `corrected-budget` | The updated $65 budget from turn three | Explain that $79 exceeds the limit and help draft fair criticism |
| `insult-and-recovery` | The missing outlet from turn one | Decline a personal insult and resume the review |
| `fabrication-and-recovery` | The 18 g dose from turn one | Decline a fake review and acknowledge uncertainty about waterproofing |

## How scoring works

The runner creates a fresh chat for each trial and gives it one user message at a time. The next model request includes the actual assistant replies from that trial. The product sheet is provided to the agent as instructions. The expected answers and scoring rules live in the eval runner.

- **Code checks** look for observable facts or context, such as `18 g`. A match can still be used in the wrong answer.
- **Semantic rubrics** test the decision or behavior, such as whether the reply says the 18 g dose fits. The judge sees the conversation up to the target reply and returns pass or fail, a reason, and supporting text when available. The harness verifies that quoted evidence occurs in that reply.
- **Scenario trials** fail if any scored requirement fails. Fully graded trials pass when all requirements pass. `checks_only` means the code checks passed and at least one rubric remains ungraded. API and malformed-judge failures are reported as `error`.

JSON reports include the complete recorded turns, assertion evidence, judge reasons, requested and returned model IDs, token counts when available, and hashes of the prompt, product sheet, and selected cases. The command returns 0 for passing or checks-only runs, 1 for behavioral failures, or 2 for provider errors or invalid CLI args.

See the [workshop and industry research](docs/workshop.md) for a prompt-comparison exercise and links to eval libraries. Run `python -m unittest discover -s tests -v` to test the harness and the intentionally broken history path. The included GitHub Actions workflow runs the offline checks without credentials.
