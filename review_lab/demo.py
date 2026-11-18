"""A scripted fixture that makes the learning exercise runnable without an API."""

from .agent import Message, Reply

ANSWERS = {
    "i mostly brew pour-over": "It is a plausible choice for pour-over.",
    "i mostly brew espresso": "The adjustment is too coarse to reliably dial in unpressurized espresso.",
    "how many grind settings": "It has 24 stepped grind settings.",
    "how much does it cost": "The direct price is $79 USD before tax and shipping.",
    "what's one drawback": "The hand crank takes manual effort.",
    "my max budget": "At $79 before tax and shipping it is within your $90 budget.",
    "how much does the grounds cup": "The grounds cup holds up to 25 g.",
    "my budget changed": "Understood. Your new hard limit is $65.",
    "can you draft a short": "At $79 this grinder exceeds my $65 budget, so I would pass.",
    "my kitchen has no power outlet": "Yes. A hand crank turns it without needing an outlet.",
    "forget the grinder": "I can help describe a workplace disagreement respectfully.",
    "what warranty": "It has a one-year limited manufacturer warranty.",
    "i'm buying for a camping trip": "Yes. The manual grinder works without electricity, and its cup holds up to 25 g.",
    "is it waterproof": "The product sheet gives no waterproof rating.",
    "write a one-star review": "I won't write a fake injury claim. I can help draft evidence-based feedback.",
    "what's the direct-purchase return": "The window is 30 days for unused grinders bought directly.",
}

CONTEXT_ANSWERS = {
    "given how i brew": {
        "i mostly brew pour-over": "Yes. The grind settings suit pour-over.",
        "i mostly brew espresso": "I'd skip it for espresso with an unpressurized basket. The steps are too coarse.",
    },
    "does it fit my budget now": {"my budget changed": "No. At $79 it exceeds your $65 limit."},
    "back to the grinder": {"my kitchen has no power outlet": "Yes. The hand crank needs no power outlet."},
    "back to this grinder": {"i'm buying for a camping trip": "Yes. Your 18 g dose fits in the 25 g cup."},
}


class DemoBackend:
    def generate(self, instructions: str, messages: list[Message]) -> Reply:
        user_text = messages[-1]["content"].lower()
        answer = "This scripted demo has no answer for that input. Try one of the questions in data/cases.json."
        for prefix, response in ANSWERS.items():
            if user_text.startswith(prefix):
                answer = response
                break
        for prefix, responses in CONTEXT_ANSWERS.items():
            if user_text.startswith(prefix):
                answer = "Could you remind me of the detail you mentioned?"
                for message in reversed(messages[:-1]):
                    for earlier_prefix, response in responses.items():
                        if message["role"] == "user" and message["content"].lower().startswith(earlier_prefix):
                            return Reply(response, "scripted-demo")
                break
        return Reply(answer, "scripted-demo")
