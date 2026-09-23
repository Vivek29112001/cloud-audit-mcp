# from __future__ import annotations

# import json
# from typing import Any

# from groq import Groq

# from app.core.config import settings


# class GroqAnswerGenerator:

#     def __init__(self) -> None:

#         if not settings.groq_api_key:
#             raise RuntimeError(
#                 "GROQ_API_KEY is not configured."
#             )

#         self._client = Groq(
#             api_key=settings.groq_api_key
#         )

#     def generate(
#         self,
#         *,
#         question: str,
#         intent: dict[str, Any],
#         aws_result: dict[str, Any],
#     ) -> str:

#         system_prompt = """
# You are the response formatter for a read-only
# AWS cloud audit application.

# The AWS data supplied to you came from live AWS API
# calls executed through the official AWS MCP Server.

# Rules:

# - Answer only from supplied AWS evidence.
# - Never invent resources.
# - Never invent AWS Regions.
# - Never invent counts.
# - Never claim a security problem unless the supplied
#   data directly supports that conclusion.
# - If some Regions failed, clearly mention partial coverage.
# - If zero matching resources are present, say so.
# - Prefer resource IDs, names, states and Regions when relevant.
# - Keep answers concise and audit-friendly.
# - Do not expose credentials, secrets, tokens, or unnecessary
#   sensitive values.
# """

#         payload = {
#             "question": question,
#             "intent": intent,
#             "aws_result": aws_result,
#         }

#         response = (
#             self._client
#             .chat.completions
#             .create(
#                 model=(
#                     settings.groq_intent_model
#                 ),
#                 temperature=0,
#                 messages=[
#                     {
#                         "role": "system",
#                         "content":
#                             system_prompt,
#                     },
#                     {
#                         "role": "user",
#                         "content": json.dumps(
#                             payload,
#                             default=str,
#                         ),
#                     },
#                 ],
#             )
#         )

#         content = (
#             response
#             .choices[0]
#             .message
#             .content
#         )

#         if not content:
#             return (
#                 "The AWS query completed, "
#                 "but no formatted answer "
#                 "was generated."
#             )

#         return content

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
    @staticmethod
    def _bounded_snapshot_payload(
        *,
        question: str,
        snapshot_evidence: dict[str, Any],
        conversation_context: str | None,
        max_chars: int = 14000,
    ) -> str:
        """Build a hard-bounded JSON prompt for the snapshot formatter.

        The full immutable scan remains in SQLite. Only the formatter payload
        is reduced. The reduction is generic and does not contain AWS service
        allowlists or mappings.
        """
        evidence = snapshot_evidence
        payload = {
            "question": question,
            "conversation_context": (conversation_context or "")[-1500:],
            "snapshot_evidence": evidence,
        }
        encoded = json.dumps(payload, default=str, separators=(",", ":"))
        if len(encoded) <= max_chars:
            return encoded

        resources = evidence.get("resources") or {}
        billing = evidence.get("billing") or {}
        classification = evidence.get("classification") or {}
        regions = evidence.get("regions") or {}

        compact_classification: dict[str, Any] = {
            "billing_available": classification.get("billing_available"),
        }
        for key in (
            "primary_paid_services",
            "zero_cost_services",
            "supporting_services",
            "discovered_unbilled_services",
            "billing_only_services",
            "non_positive_billing_services",
        ):
            compact_classification[key] = (classification.get(key) or [])[:6]
        for key in (
            "paid_regions",
            "used_unbilled_regions",
            "enabled_unused_regions",
            "billed_only_regions",
        ):
            compact_classification[key] = (classification.get(key) or [])[:12]
        compact_classification["relationships"] = (classification.get("relationships") or [])[:8]

        compact_evidence = {
            "evidence_source": evidence.get("evidence_source"),
            "scan_id": evidence.get("scan_id"),
            "scan_status": evidence.get("scan_status"),
            "scan_completed_at": evidence.get("scan_completed_at"),
            "selected_context": evidence.get("selected_context") or {},
            "account": evidence.get("account") or {},
            "summary": evidence.get("summary") or {},
            "resources": {
                "total_resources": resources.get("total_resources"),
                "used_regions": (resources.get("used_regions") or [])[:15],
                "detected_services": (resources.get("detected_services") or [])[:12],
                "matching_resources": (resources.get("matching_resources") or [])[:8],
                "matching_resource_count": resources.get("matching_resource_count"),
                "resource_evidence_truncated": resources.get("resource_evidence_truncated"),
            },
            "billing": {
                "available": billing.get("available"),
                "period_start": billing.get("period_start"),
                "period_end_exclusive": billing.get("period_end_exclusive"),
                "currency": billing.get("currency"),
                "total_cost": billing.get("total_cost"),
                "service_costs": (billing.get("service_costs") or [])[:10],
                "region_costs": (billing.get("region_costs") or [])[:10],
                "components": (billing.get("components") or [])[:4],
            },
            "classification": compact_classification,
            "regions": {
                "total_regions": regions.get("total_regions"),
                "enabled_regions": regions.get("enabled_regions"),
                "disabled_regions": regions.get("disabled_regions"),
                "regions": (regions.get("regions") or [])[:12],
            },
            "scan_warnings": (evidence.get("scan_warnings") or [])[:5],
        }
        payload["snapshot_evidence"] = compact_evidence
        encoded = json.dumps(payload, default=str, separators=(",", ":"))

        if len(encoded) <= max_chars:
            return encoded

        # Final safety valve: keep only the most relevant top-level facts.
        minimal = {
            "question": question,
            "conversation_context": (conversation_context or "")[-600:],
            "snapshot_evidence": {
                "evidence_source": compact_evidence.get("evidence_source"),
                "scan_id": compact_evidence.get("scan_id"),
                "scan_completed_at": compact_evidence.get("scan_completed_at"),
                "selected_context": compact_evidence.get("selected_context"),
                "summary": compact_evidence.get("summary"),
                "resources": {
                    "matching_resource_count": compact_evidence["resources"].get("matching_resource_count"),
                    "matching_resources": compact_evidence["resources"].get("matching_resources", [])[:4],
                    "used_regions": compact_evidence["resources"].get("used_regions", [])[:10],
                },
                "billing": {
                    "available": compact_evidence["billing"].get("available"),
                    "currency": compact_evidence["billing"].get("currency"),
                    "total_cost": compact_evidence["billing"].get("total_cost"),
                    "service_costs": compact_evidence["billing"].get("service_costs", [])[:5],
                },
                "classification": {
                    key: value[:4] if isinstance(value, list) else value
                    for key, value in compact_classification.items()
                    if key != "relationships"
                },
            },
        }
        encoded = json.dumps(minimal, default=str, separators=(",", ":"))
        if len(encoded) <= max_chars:
            return encoded

        # Ultra-minimal valid JSON. Never slice serialized JSON because that
        # could produce an invalid formatter request.
        ultra_minimal = {
            "question": question[:1000],
            "snapshot_evidence": {
                "evidence_source": evidence.get("evidence_source"),
                "scan_id": evidence.get("scan_id"),
                "scan_completed_at": evidence.get("scan_completed_at"),
                "selected_context": evidence.get("selected_context") or {},
                "summary": evidence.get("summary") or {},
                "matching_resource_count": resources.get("matching_resource_count"),
                "matching_resources": (resources.get("matching_resources") or [])[:2],
            },
        }
        return json.dumps(ultra_minimal, default=str, separators=(",", ":"))

    def generate_snapshot(
        self,
        *,
        question: str,
        snapshot_evidence: dict[str, Any],
        conversation_context: str | None = None,
    ) -> str:
        """Answer only from one persisted immutable discovery snapshot."""
        system_prompt = """
You are the response formatter for a read-only AWS cloud audit application.

The supplied evidence is from a SAVED, IMMUTABLE discovery snapshot.
It is not guaranteed to represent the AWS account right now.

Rules:
- Answer only from supplied snapshot evidence.
- Never invent resources, Regions, costs, relationships, or configuration.
- Clearly frame facts as being true at the snapshot scan time.
- If the requested fact is not present in snapshot evidence, say that the
  saved scan does not contain enough evidence and a live query/refresh may
  be needed.
- Use the selected structured context when supplied.
- Recent conversation is for reference resolution only, not evidence.
- If resource evidence is truncated, do not claim it is an exhaustive list.
- Keep answers concise and audit-friendly.
- Never expose credentials, secrets, or tokens.
"""
        user_payload = self._bounded_snapshot_payload(
            question=question,
            snapshot_evidence=snapshot_evidence,
            conversation_context=conversation_context,
        )
        response = self._client.chat.completions.create(
            model=settings.groq_intent_model,
            temperature=0,
            max_tokens=700,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_payload},
            ],
        )
        content = response.choices[0].message.content
        return content or "The saved AWS snapshot contains no formatted answer for this question."

