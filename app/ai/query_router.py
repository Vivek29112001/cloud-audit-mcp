from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Any, Awaitable, Callable

from app.ai.answer_generator import GroqAnswerGenerator
from app.ai.groq_client import GroqIntentClient
from app.ai.s3_audit_answer import generate_s3_audit_answer
from app.ai.snapshot_answer import try_generate_snapshot_answer
from app.ai.snapshot_evidence import build_snapshot_evidence
from app.providers.aws.audits.s3_security import (
    S3SecurityAuditExecutor,
    S3SecurityAuditRequest,
)
from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.mcp_client import AWSMCPClient
from app.providers.aws.query.multi_region_executor import AWSMultiRegionQueryExecutor
from app.providers.aws.query.read_only_validator import (
    AWSReadOnlyOperationValidator,
    UnsafeAWSOperationError,
)
from app.providers.aws.query.region_resolver import AWSQueryRegionResolver


logger = logging.getLogger(__name__)

CredentialLoader = Callable[[], Awaitable[AWSCredentials]]


class AWSQueryRouter:
    """
    Routes natural-language AWS audit questions to either:
      1. saved immutable scan evidence,
      2. a deterministic service-specific audit executor, or
      3. one generic live read-only AWS operation.

    Service-specific audit executors are used for questions that inherently
    require dependent multi-step evidence collection (for example, an S3
    encryption + object-name/metadata audit). This avoids forcing a complex
    audit into the generic one-operation intent schema.
    """

    USER_UNDERSTANDING_ERROR = (
        "Unable to understand the question. Please try again or rephrase your request."
    )
    USER_EXECUTION_ERROR = (
        "I couldn't complete that AWS request right now. Please try again."
    )
    USER_FORMATTING_ERROR = (
        "I couldn't complete that request right now. Please try again."
    )

    def __init__(self) -> None:
        self._intent_client = GroqIntentClient()
        self._validator = AWSReadOnlyOperationValidator()
        self._region_resolver = AWSQueryRegionResolver()
        self._executor = AWSMultiRegionQueryExecutor()
        self._answer_generator = GroqAnswerGenerator()
        self._s3_audit_executor = S3SecurityAuditExecutor()

    async def execute(
        self,
        *,
        question: str,
        scan_result: dict[str, Any],
        credential_loader: CredentialLoader | None = None,
        conversation_context: str | None = None,
        selected_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        started = perf_counter()
        timings: dict[str, int] = {}
        selected_context = dict(selected_context or {})

        # ------------------------------------------------------------
        # Deterministic multi-step S3 audit path.
        # This runs BEFORE the single-operation Groq planner because an
        # encryption/public-access/sensitivity audit requires multiple
        # dependent AWS calls per dynamically discovered bucket.
        # ------------------------------------------------------------
        s3_audit_request = S3SecurityAuditRequest.from_question(
            question,
            selected_context,
        )
        if s3_audit_request is not None:
            return await self._execute_s3_audit(
                started=started,
                timings=timings,
                question=question,
                scan_result=scan_result,
                credential_loader=credential_loader,
                selected_context=selected_context,
                request=s3_audit_request,
            )

        # ------------------------------------------------------------
        # Generic intent planning.
        # Internal provider/schema exceptions are logged, never shown to
        # the end user as raw 400/json_validate_failed payloads.
        # ------------------------------------------------------------
        t = perf_counter()
        try:
            intent = self._intent_client.parse_aws_question(
                question,
                conversation_context=conversation_context,
                selected_context=selected_context,
            )
        except Exception:
            logger.exception("AWS intent planning failed")
            return self._error(
                started,
                timings,
                "INTENT_PLANNING_FAILED",
                {},
                self.USER_UNDERSTANDING_ERROR,
            )

        timings["intent_ms"] = self._ms(t)
        intent_dict = intent.model_dump(mode="json")

        if str(intent.operation or "").strip().lower() == "outofscope":
            return self._error(
                started,
                timings,
                "OUT_OF_SCOPE",
                intent_dict,
                (
                    "This chat is scoped to the selected AWS account, saved "
                    "discovery snapshots, billing, configuration, and read-only "
                    "cloud-audit questions."
                ),
            )

        # ------------------------------------------------------------
        # Saved snapshot path.
        # ------------------------------------------------------------
        if not intent.requires_live_data:
            evidence = build_snapshot_evidence(
                scan_result=scan_result,
                selected_context=selected_context,
                intent=intent_dict,
            )
            answer = try_generate_snapshot_answer(
                question=question,
                snapshot_evidence=evidence,
            )

            t = perf_counter()
            try:
                if answer is None:
                    answer = self._answer_generator.generate_snapshot(
                        question=question,
                        snapshot_evidence=evidence,
                        conversation_context=conversation_context,
                    )
            except Exception:
                logger.exception("Snapshot answer generation failed")
                return self._error(
                    started,
                    timings,
                    "ANSWER_GENERATION_FAILED",
                    intent_dict,
                    self.USER_FORMATTING_ERROR,
                    data=evidence,
                )

            timings["answer_ms"] = self._ms(t)
            timings["total_ms"] = self._ms(started)

            return {
                "status": "SUCCESS",
                "source": "PERSISTED_DISCOVERY_SNAPSHOT",
                "scan_id": scan_result.get("scan_id"),
                "intent": intent_dict,
                "selected_context": selected_context,
                "answer": answer,
                "data": evidence,
                "warnings": scan_result.get("warnings") or [],
                "timings": timings,
                "response_time_ms": timings["total_ms"],
                "response_time_seconds": round(timings["total_ms"] / 1000, 2),
            }

        # ------------------------------------------------------------
        # Generic single-operation live path.
        # ------------------------------------------------------------
        if credential_loader is None:
            return self._error(
                started,
                timings,
                "AWS_AUTHORIZATION_REQUIRED",
                intent_dict,
                (
                    "AWS authorization is required to complete this request. "
                    "Please reconnect or re-authorize the account."
                ),
            )

        try:
            t = perf_counter()
            credentials = await credential_loader()
            timings["automatic_auth_ms"] = self._ms(t)
        except Exception:
            logger.exception("Automatic AWS authentication failed")
            return self._error(
                started,
                timings,
                "AWS_AUTHORIZATION_REQUIRED",
                intent_dict,
                (
                    "AWS authorization is required to complete this request. "
                    "Please reconnect or re-authorize the account."
                ),
            )

        service = (intent.service or "").strip().lower()
        operation = (intent.operation or "").strip()

        if not service or not operation:
            return self._error(
                started,
                timings,
                "INVALID_LIVE_PLAN",
                intent_dict,
                self.USER_UNDERSTANDING_ERROR,
            )

        try:
            self._validator.validate(service=service, operation=operation)
        except UnsafeAWSOperationError:
            logger.warning(
                "Blocked non-read-only AWS operation: service=%s operation=%s",
                service,
                operation,
            )
            return self._error(
                started,
                timings,
                "OPERATION_BLOCKED",
                intent_dict,
                "That AWS operation is not permitted in read-only audit mode.",
            )

        detected = (scan_result.get("resources") or {}).get("detected_services", [])
        entry = next(
            (
                item
                for item in detected
                if str(item.get("service", "")).strip().lower() == service
            ),
            None,
        )

        regions = self._region_resolver.resolve(
            service=service,
            requested_region=intent.region,
            service_entry=entry,
            fallback_region=credentials.default_region,
        )

        if not regions:
            return self._error(
                started,
                timings,
                "NO_QUERY_REGION",
                intent_dict,
                self.USER_EXECUTION_ERROR,
            )

        t = perf_counter()
        try:
            async with AWSMCPClient(credentials) as mcp:
                execution = await self._executor.execute(
                    credentials=credentials,
                    service=service,
                    operation=operation,
                    regions=regions,
                    params=intent.get_params(),
                    mcp=mcp,
                )
        except Exception:
            logger.exception(
                "AWS MCP generic query failed: service=%s operation=%s",
                service,
                operation,
            )
            return self._error(
                started,
                timings,
                "AWS_MCP_EXECUTION_FAILED",
                intent_dict,
                self.USER_EXECUTION_ERROR,
            )

        timings["aws_mcp_ms"] = self._ms(t)
        data = execution.model_dump(mode="json")

        if not execution.successful_regions:
            logger.warning(
                "AWS query failed in all target Regions: service=%s operation=%s warnings=%s",
                service,
                operation,
                execution.warnings,
            )
            return self._error(
                started,
                timings,
                "AWS_QUERY_FAILED",
                intent_dict,
                self.USER_EXECUTION_ERROR,
                data=data,
                warnings=execution.warnings,
            )

        t = perf_counter()
        try:
            answer = self._answer_generator.generate(
                question=question,
                intent=intent_dict,
                aws_result=data,
            )
        except Exception:
            logger.exception("Live AWS answer generation failed")
            return self._error(
                started,
                timings,
                "ANSWER_GENERATION_FAILED",
                intent_dict,
                self.USER_FORMATTING_ERROR,
                data=data,
                warnings=execution.warnings,
            )

        timings["answer_ms"] = self._ms(t)
        timings["total_ms"] = self._ms(started)

        return {
            "status": "SUCCESS",
            "source": "LIVE_AWS_MCP_AUTO_AUTH",
            "scan_id": scan_result.get("scan_id"),
            "intent": intent_dict,
            "selected_context": selected_context,
            "answer": answer,
            "data": data,
            "warnings": execution.warnings,
            "timings": timings,
            "response_time_ms": timings["total_ms"],
            "response_time_seconds": round(timings["total_ms"] / 1000, 2),
        }

    async def _execute_s3_audit(
        self,
        *,
        started: float,
        timings: dict[str, int],
        question: str,
        scan_result: dict[str, Any],
        credential_loader: CredentialLoader | None,
        selected_context: dict[str, Any],
        request: S3SecurityAuditRequest,
    ) -> dict[str, Any]:
        intent_dict = {
            "service": "s3",
            "operation": "S3SecurityAudit",
            "region": None,
            "params_json": json.dumps(request.as_dict(), separators=(",", ":")),
            "resource_id": None,
            "requires_live_data": True,
        }

        if credential_loader is None:
            return self._error(
                started,
                timings,
                "AWS_AUTHORIZATION_REQUIRED",
                intent_dict,
                (
                    "AWS authorization is required to complete this request. "
                    "Please reconnect or re-authorize the account."
                ),
            )

        try:
            t = perf_counter()
            credentials = await credential_loader()
            timings["automatic_auth_ms"] = self._ms(t)
        except Exception:
            logger.exception("Automatic AWS authentication failed for S3 audit")
            return self._error(
                started,
                timings,
                "AWS_AUTHORIZATION_REQUIRED",
                intent_dict,
                (
                    "AWS authorization is required to complete this request. "
                    "Please reconnect or re-authorize the account."
                ),
            )

        t = perf_counter()
        try:
            async with AWSMCPClient(credentials) as mcp:
                data = await self._s3_audit_executor.execute(
                    mcp=mcp,
                    request=request,
                )
        except Exception:
            logger.exception("S3 multi-step security audit failed")
            return self._error(
                started,
                timings,
                "AWS_MCP_EXECUTION_FAILED",
                intent_dict,
                self.USER_EXECUTION_ERROR,
            )

        timings["aws_mcp_ms"] = self._ms(t)

        # Deterministic formatting deliberately avoids a second Groq call for
        # this evidence-heavy audit. This prevents a completed audit from being
        # lost to an answer-formatting 400/413.
        t = perf_counter()
        answer = generate_s3_audit_answer(
            audit_result=data,
            question=question,
        )
        timings["answer_ms"] = self._ms(t)
        timings["total_ms"] = self._ms(started)

        warnings: list[Any] = list(data.get("warnings") or [])
        for bucket in data.get("buckets") or []:
            for warning in bucket.get("warnings") or []:
                warnings.append(
                    {
                        "bucket": bucket.get("name"),
                        **warning,
                    }
                )

        return {
            "status": "SUCCESS",
            "source": "LIVE_AWS_MCP_AUTO_AUTH",
            "scan_id": scan_result.get("scan_id"),
            "intent": intent_dict,
            "selected_context": selected_context,
            "answer": answer,
            "data": data,
            "warnings": warnings,
            "timings": timings,
            "response_time_ms": timings["total_ms"],
            "response_time_seconds": round(timings["total_ms"] / 1000, 2),
        }

    @staticmethod
    def _ms(started: float) -> int:
        return round((perf_counter() - started) * 1000)

    @classmethod
    def _error(
        cls,
        started: float,
        timings: dict[str, int],
        status: str,
        intent: dict[str, Any],
        answer: str,
        data: Any = None,
        warnings: list[Any] | None = None,
    ) -> dict[str, Any]:
        timings["total_ms"] = cls._ms(started)
        out: dict[str, Any] = {
            "status": status,
            "intent": intent,
            "answer": answer,
            "warnings": warnings or [],
            "timings": timings,
            "response_time_ms": timings["total_ms"],
            "response_time_seconds": round(timings["total_ms"] / 1000, 2),
        }
        if data is not None:
            out["data"] = data
        return out
