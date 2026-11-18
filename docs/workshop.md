# Multi-turn evaluation workshop

## Exercise 1. Prove the eval can see a failure

1. Run the full-history demo and the latest-message-only demo from the README.
2. In each report, find `pour-over` and `espresso`. Read turn one and then turn four. The fixed follow-up is identical between the cases. A recommendation that remains unchanged across these different setups is worth investigating even if it mentions both brewing methods.
3. Look at `insult-and-recovery`. Turn three tests the boundary. Turn four tests whether the agent can continue the product review by recovering the shopper's original constraint. A refusal on turn three cannot compensate for a failed recovery.
4. Read a rubric in `data/cases.json` and apply it yourself to the transcript. Compare it with the adjacent code check. For instance, the word `espresso` is enough to satisfy the recall probe, while the rubric requires the recommendation to go in the correct direction.

The history control changes one configuration variable and removes every earlier message from the candidate's input. It shows that the task depends on prior messages. The paired conversation changes only the first user message in the script and tests whether the context changes the conclusion. Earlier assistant replies may also change as a consequence.

## Exercise 2. Compare a baseline and a candidate prompt

Run the live suite with `--repeat 3` if you have API access. Start with the paired cases to keep the cost and transcripts small.

```bash
python -m review_lab eval --backend openai --case pour-over --case espresso \
  --repeat 3 --output reports/baseline.json

cp data/agent-prompt.txt candidate-prompt.txt
# Edit candidate-prompt.txt before the next command.
python -m review_lab eval --backend openai --case pour-over --case espresso \
  --prompt candidate-prompt.txt --repeat 3 --output reports/candidate.json
```

Change one thing, such as asking the agent to explicitly state the earlier brewing method when giving a recommendation. Hold the case set, models, and judge fixed. Compare the per-criterion results, especially turn four, then read the transcripts behind each failure or score change. Three repeats can surface variation in this exercise. The suite is too small to estimate how the agent would perform across shoppers.

The CLI reports how many cases passed every observed trial in a judged run. Multiple trials matter because both the candidate and the judge can vary. The original τ-bench paper defines pass^k to measure consistency over k trials in tool-using conversations. This lab's count is a simple observed all-trials result for its fixed, small suite. [τ-bench](https://arxiv.org/abs/2406.12045), [Anthropic on trials and agent evals](https://www.anthropic.com/research/demystifying-evals-for-ai-agents)

## Exercise 3. Add one case and calibrate the judge

1. Copy a case in `data/cases.json` to a new ID. Give it a user detail early and a later question whose answer depends on that detail.
2. Add a `match` mapping for a narrow fact and a `rubric` mapping for the intended behavior. The agent receives only the `user` content.
3. Write one clearly good reply and one plausible but wrong reply in your notes. Apply the rubric to both. If the judgments are hard to agree on, tighten the wording.
4. Run the new case with `--backend openai --case YOUR_ID`. The default demo has canned answers for the bundled scripts. Inspect a few judge decisions by hand, especially when the evidence quote is correct but the conclusion seems wrong.
5. Keep some cases aside while editing the prompt. When a real failure appears, convert it into a reusable test and check it alongside the cases that were already working.

## Industry approaches

A common starting point is a versioned dataset with typical, edge, and adversarial examples. Use code for facts you can check directly, rubrics for behavior that can be expressed in several ways, and human review to calibrate the grader. Log full traces so failures can be inspected at the turn where they occurred. Add continuous regression checks as the suite becomes reliable. When the agent can take actions, verify the resulting application state independently of what the assistant says it did. [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices), [Anthropic agent-eval guide](https://www.anthropic.com/research/demystifying-evals-for-ai-agents), [τ-bench](https://arxiv.org/abs/2406.12045)

| Tool | Where it fits |
| --- | --- |
| Promptfoo | Configuration-driven prompt and model comparisons. Its chat configuration can replay a conversation and feed earlier outputs into later turns. [Chat and multi-turn docs](https://www.promptfoo.dev/docs/configuration/chat/) |
| DeepEval | Python conversational test cases, simulated users, and metrics for properties such as turn relevance and knowledge retention. [Simulation guide](https://deepeval.com/guides/guides-multi-turn-simulation), [Multi-turn metrics](https://deepeval.com/guides/guides-multi-turn-evaluation-metrics) |
| LangSmith | Datasets and pre-release evaluation plus online scoring of traces and conversation threads. [Evaluation types](https://docs.langchain.com/langsmith/evaluation-types), [Online evaluator docs](https://docs.langchain.com/langsmith/online-evaluations-llm-as-judge) |
| Braintrust | An experiment workflow for versioned tasks, scorers, traces, and side-by-side run analysis. [Experiments guide](https://docs.braintrust.dev/evaluate/run-evaluations) |
| OpenAI Evals | Managed datasets, graders, and eval runs, with trace grading available for OpenAI agent workflows. [Working with evals](https://developers.openai.com/api/docs/guides/evals), [Agent workflow evaluation](https://developers.openai.com/api/docs/guides/agent-evals) |

This lab uses a small Python runner so you can read the entire path from a user message to a score. A fixed script is a practical first step because every candidate gets the same user questions. Simulated users are a follow-up when you need the conversation to branch based on an agent's answers. Use a small, human-reviewed sample to check that those simulated conversations represent the behavior you want to measure. [DeepEval simulation guide](https://deepeval.com/guides/guides-multi-turn-simulation), [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
