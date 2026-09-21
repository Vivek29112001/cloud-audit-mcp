from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConversationMessage:
    role: str
    content: str


@dataclass
class ConversationContext:

    messages: list[
        ConversationMessage
    ]

    MAX_CONTEXT_CHARS = 12000

    def as_text(self) -> str:

        if not self.messages:
            return ""

        lines: list[str] = []

        for message in self.messages:

            role = (
                "User"
                if message.role == "user"
                else "Assistant"
            )

            lines.append(
                f"{role}: {message.content}"
            )

        text = "\n".join(
            lines
        )

        if (
            len(text)
            > self.MAX_CONTEXT_CHARS
        ):
            text = text[
                -self.MAX_CONTEXT_CHARS:
            ]

        return text