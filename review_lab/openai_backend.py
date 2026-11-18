"""OpenAI Responses API adapter shared by the agent and the optional judge."""

from typing import Any

from .agent import Message, Reply


class ProviderError(RuntimeError):
    """A request or response failure, distinct from a low eval score."""


class OpenAIBackend:
    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    def generate(
        self,
        instructions: str,
        messages: list[Message],
        *,
        schema: dict | None = None,
    ) -> Reply:
        options = {}
        if schema is not None:
            options["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "turn_scores",
                    "strict": True,
                    "schema": schema,
                }
            }
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=messages,
                store=False,
                reasoning={"effort": "low"},
                max_output_tokens=2500 if schema else 1500,
                **options,
            )
        except Exception as exc:
            # Avoid storing provider exception bodies alongside transcripts.
            code = getattr(exc, "status_code", None)
            detail = f" (HTTP {code})" if code else ""
            raise ProviderError(f"{self.model}: {type(exc).__name__}{detail}") from exc

        if response.status != "completed":
            reason = getattr(response.incomplete_details, "reason", None)
            raise ProviderError(f"{self.model}: response {response.status} ({reason or 'no detail'})")
        text = response.output_text.strip()
        if not text and schema is None:
            refusals = [
                part.refusal
                for item in response.output
                if item.type == "message"
                for part in item.content
                if part.type == "refusal"
            ]
            text = "\n".join(refusals).strip()
        if not text:
            raise ProviderError(f"{self.model}: no usable response text")

        usage = response.usage
        tokens = {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens} if usage else None
        return Reply(text, response.model, tokens)
