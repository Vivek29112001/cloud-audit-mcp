from __future__ import annotations

import json
from typing import Any

from groq import Groq

from app.core.config import settings


class GroqAnswerGenerator:

    def __init__(self) -> None:

        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not configured."
            )

        self._client = Groq(
            api_key=settings.groq_api_key
        )

    def generate(
        self,
        *,
        question: str,
        intent: dict[str, Any],
        aws_result: dict[str, Any],
    ) -> str:

        system_prompt = """
You are the response formatter for a read-only
AWS cloud audit application.

The AWS data supplied to you came from live AWS API
calls executed through the official AWS MCP Server.

Rules:

- Answer only from supplied AWS evidence.
- Never invent resources.
- Never invent AWS Regions.
- Never invent counts.
- Never claim a security problem unless the supplied
  data directly supports that conclusion.
- If some Regions failed, clearly mention partial coverage.
- If zero matching resources are present, say so.
- Prefer resource IDs, names, states and Regions when relevant.
- Keep answers concise and audit-friendly.
- Do not expose credentials, secrets, tokens, or unnecessary
  sensitive values.
"""

        payload = {
            "question": question,
            "intent": intent,
            "aws_result": aws_result,
        }

        response = (
            self._client
            .chat.completions
            .create(
                model=(
                    settings.groq_intent_model
                ),
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content":
                            system_prompt,
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            payload,
                            default=str,
                        ),
                    },
                ],
            )
        )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not content:
            return (
                "The AWS query completed, "
                "but no formatted answer "
                "was generated."
            )

        return content