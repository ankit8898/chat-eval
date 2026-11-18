"""The chat path used by both the eval runner and interactive mode."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, TypedDict

DATA = Path(__file__).resolve().parent.parent / "data"
DEFAULT_MODEL = "gpt-6.2-sol"


class Message(TypedDict):
    role: Literal["user", "assistant"]
    content: str


@dataclass
class Reply:
    text: str
    model: str
    usage: dict[str, int] | None = None


class Backend(Protocol):
    def generate(self, instructions: str, messages: list[Message]) -> Reply: ...


def instructions(prompt: str, product: str) -> str:
    return f"{prompt.rstrip()}\n\n{product.rstrip()}"


@dataclass
class Chat:
    backend: Backend
    instructions: str
    history_mode: Literal["full", "latest"] = "full"
    history: list[Message] = field(default_factory=list, init=False)

    def reply(self, user_text: str) -> Reply:
        question: Message = {"role": "user", "content": user_text}
        visible = self.history if self.history_mode == "full" else []
        reply = self.backend.generate(self.instructions, [*visible, question])
        self.history.extend([question, {"role": "assistant", "content": reply.text}])
        return reply
