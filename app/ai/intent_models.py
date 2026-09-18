from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


class AWSQueryIntent(BaseModel):
    """
    Structured plan produced by Groq for one read-only AWS query.

    params_json is intentionally kept as a JSON string because strict LLM
    structured-output schemas are more reliable when the arbitrary AWS API
    parameters are encoded as a string rather than as an open-ended object.
    """

    service: str
    operation: str
    region: str | None = None
    params_json: str = "{}"
    resource_id: str | None = None
    requires_live_data: bool = True

    def get_params(self) -> dict[str, Any]:
        """Decode params_json into a dictionary for the generic AWS executor."""
        try:
            value = json.loads(self.params_json or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Groq returned invalid params_json."
            ) from exc

        if not isinstance(value, dict):
            raise ValueError(
                "params_json must represent a JSON object."
            )

        return value

    @property
    def params(self) -> dict[str, Any]:
        """Compatibility property for existing router/executor code."""
        return self.get_params()
