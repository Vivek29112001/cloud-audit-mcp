# from __future__ import annotations

# from time import perf_counter
# from typing import Any

# from app.ai.answer_generator import (
#     GroqAnswerGenerator,
# )

# from app.ai.groq_client import (
#     GroqIntentClient,
# )

# from app.providers.aws.credentials import (
#     AWSCredentials,
# )

# from app.providers.aws.mcp_client import (
#     AWSMCPClient,
# )

# from app.providers.aws.query.multi_region_executor import (
#     AWSMultiRegionQueryExecutor,
# )

# from app.providers.aws.query.read_only_validator import (
#     AWSReadOnlyOperationValidator,
#     UnsafeAWSOperationError,
# )

# from app.providers.aws.query.region_resolver import (
#     AWSQueryRegionResolver,
# )


# class AWSQueryRouter:

#     def __init__(self) -> None:

#         self._intent_client = (
#             GroqIntentClient()
#         )

#         self._validator = (
#             AWSReadOnlyOperationValidator()
#         )

#         self._region_resolver = (
#             AWSQueryRegionResolver()
#         )

#         self._executor = (
#             AWSMultiRegionQueryExecutor()
#         )

#         self._answer_generator = (
#             GroqAnswerGenerator()
#         )

#     async def execute(
#         self,
#         *,
#         question: str,
#         credentials: AWSCredentials,
#         scan_result: dict[str, Any],
#         conversation_context: str | None = None,
#     ) -> dict[str, Any]:

#         #
#         # -------------------------------------------------
#         # TOTAL QUERY TIMER
#         # -------------------------------------------------
#         #

#         query_started = (
#             perf_counter()
#         )

#         timings: dict[
#             str,
#             int,
#         ] = {}

#         #
#         # -------------------------------------------------
#         # 1. NLP QUERY PLAN
#         # -------------------------------------------------
#         #

#         stage_started = (
#             perf_counter()
#         )

#         try:

#             intent = (
#                 self._intent_client
#                 .parse_aws_question(
#                     question,
#                     conversation_context=(
#                         conversation_context
#                     ),
#                 )
#             )

#         except Exception as exc:

#             timings[
#                 "intent_ms"
#             ] = self._elapsed_ms(
#                 stage_started
#             )

#             return self._error_response(
#                 query_started=(
#                     query_started
#                 ),

#                 timings=timings,

#                 status=(
#                     "INTENT_PLANNING_FAILED"
#                 ),

#                 intent={},

#                 answer=(
#                     "Unable to understand the "
#                     "AWS question: "
#                     f"{exc}"
#                 ),
#             )

#         timings[
#             "intent_ms"
#         ] = self._elapsed_ms(
#             stage_started
#         )

#         service = (
#             intent.service
#             .strip()
#             .lower()
#         )

#         operation = (
#             intent.operation
#             .strip()
#         )

#         #
#         # -------------------------------------------------
#         # 2. READ-ONLY SAFETY VALIDATION
#         # -------------------------------------------------
#         #

#         try:

#             self._validator.validate(
#                 service=service,
#                 operation=operation,
#             )

#         except UnsafeAWSOperationError as exc:

#             return self._error_response(
#                 query_started=(
#                     query_started
#                 ),

#                 timings=timings,

#                 status=(
#                     "OPERATION_BLOCKED"
#                 ),

#                 intent=(
#                     intent.model_dump(
#                         mode="json"
#                     )
#                 ),

#                 answer=str(
#                     exc
#                 ),
#             )

#         #
#         # -------------------------------------------------
#         # 3. CHECK BASELINE SERVICE DISCOVERY
#         # -------------------------------------------------
#         #

#         detected_services = (
#             scan_result
#             .get(
#                 "resources",
#                 {},
#             )
#             .get(
#                 "detected_services",
#                 [],
#             )
#         )

#         service_entry = next(
#             (
#                 item

#                 for item
#                 in detected_services

#                 if (
#                     item.get(
#                         "service",
#                         "",
#                     )
#                     .strip()
#                     .lower()
#                     == service
#                 )
#             ),
#             None,
#         )

#         # Resource Explorer is evidence, not an allow-list. Some AWS APIs are
#         # account/global control-plane services and might not expose resources
#         # in Resource Explorer. We therefore do not block a safe read-only query
#         # solely because the service was absent from baseline discovery.

#         #
#         # -------------------------------------------------
#         # 4. RESOLVE TARGET REGIONS
#         # -------------------------------------------------
#         #

#         target_regions = (
#             self._region_resolver
#             .resolve(
#                 service=service,

#                 requested_region=(
#                     intent.region
#                 ),

#                 service_entry=(
#                     service_entry
#                 ),

#                 fallback_region=(
#                     credentials.default_region
#                 ),
#             )
#         )

#         if not target_regions:

#             return self._error_response(
#                 query_started=(
#                     query_started
#                 ),

#                 timings=timings,

#                 status=(
#                     "NO_QUERY_REGION"
#                 ),

#                 intent=(
#                     intent.model_dump(
#                         mode="json"
#                     )
#                 ),

#                 answer=(
#                     "The query service was "
#                     "detected, but no usable "
#                     "AWS Region could be "
#                     "resolved."
#                 ),
#             )

#         #
#         # -------------------------------------------------
#         # 5. OFFICIAL AWS MCP EXECUTION
#         #
#         # One MCP session is opened for the entire query.
#         # All Region operations reuse the same session.
#         # -------------------------------------------------
#         #

#         stage_started = (
#             perf_counter()
#         )

#         try:

#             async with AWSMCPClient(
#                 credentials
#             ) as mcp:

#                 execution = (
#                     await self._executor
#                     .execute(
#                         credentials=(
#                             credentials
#                         ),

#                         service=service,

#                         operation=operation,

#                         regions=(
#                             target_regions
#                         ),

#                         params=(
#                             intent
#                             .get_params()
#                         ),

#                         mcp=mcp,
#                     )
#                 )

#         except Exception as exc:

#             timings[
#                 "aws_mcp_ms"
#             ] = self._elapsed_ms(
#                 stage_started
#             )

#             return self._error_response(
#                 query_started=(
#                     query_started
#                 ),

#                 timings=timings,

#                 status=(
#                     "AWS_MCP_EXECUTION_FAILED"
#                 ),

#                 intent=(
#                     intent.model_dump(
#                         mode="json"
#                     )
#                 ),

#                 answer=(
#                     "AWS MCP query execution "
#                     "failed: "
#                     f"{exc}"
#                 ),
#             )

#         timings[
#             "aws_mcp_ms"
#         ] = self._elapsed_ms(
#             stage_started
#         )

#         execution_dict = (
#             execution.model_dump(
#                 mode="json"
#             )
#         )

#         #
#         # -------------------------------------------------
#         # 6. VERIFY AT LEAST ONE REGION SUCCEEDED
#         # -------------------------------------------------
#         #

#         if not execution.successful_regions:

#             return self._error_response(
#                 query_started=(
#                     query_started
#                 ),

#                 timings=timings,

#                 status=(
#                     "AWS_QUERY_FAILED"
#                 ),

#                 intent=(
#                     intent.model_dump(
#                         mode="json"
#                     )
#                 ),

#                 answer=(
#                     "The AWS query failed in "
#                     "all target Regions."
#                 ),

#                 data=(
#                     execution_dict
#                 ),

#                 warnings=(
#                     execution.warnings
#                 ),
#             )

#         #
#         # -------------------------------------------------
#         # 7. GROQ ANSWER FORMATTING
#         # -------------------------------------------------
#         #

#         stage_started = (
#             perf_counter()
#         )

#         try:

#             answer = (
#                 self._answer_generator
#                 .generate(
#                     question=question,

#                     intent=(
#                         intent.model_dump(
#                             mode="json"
#                         )
#                     ),

#                     aws_result=(
#                         execution_dict
#                     ),
#                 )
#             )

#         except Exception as exc:

#             timings[
#                 "answer_ms"
#             ] = self._elapsed_ms(
#                 stage_started
#             )

#             return self._error_response(
#                 query_started=(
#                     query_started
#                 ),

#                 timings=timings,

#                 status=(
#                     "ANSWER_GENERATION_FAILED"
#                 ),

#                 intent=(
#                     intent.model_dump(
#                         mode="json"
#                     )
#                 ),

#                 answer=(
#                     "AWS data was retrieved, "
#                     "but answer formatting "
#                     "failed: "
#                     f"{exc}"
#                 ),

#                 data=(
#                     execution_dict
#                 ),

#                 warnings=(
#                     execution.warnings
#                 ),
#             )

#         timings[
#             "answer_ms"
#         ] = self._elapsed_ms(
#             stage_started
#         )

#         #
#         # -------------------------------------------------
#         # 8. TOTAL RESPONSE TIME
#         # -------------------------------------------------
#         #

#         timings[
#             "total_ms"
#         ] = self._elapsed_ms(
#             query_started
#         )

#         return {
#             "status":
#                 "SUCCESS",

#             "intent":
#                 intent.model_dump(
#                     mode="json"
#                 ),

#             "answer":
#                 answer,

#             "data":
#                 execution_dict,

#             "warnings":
#                 execution.warnings,

#             #
#             # Developer timing breakdown
#             #
#             "timings":
#                 timings,

#             #
#             # Easy frontend display
#             #
#             "response_time_ms":
#                 timings[
#                     "total_ms"
#                 ],

#             "response_time_seconds":
#                 round(
#                     timings[
#                         "total_ms"
#                     ]
#                     / 1000,
#                     2,
#                 ),
#         }

#     @staticmethod
#     def _elapsed_ms(
#         started_at: float,
#     ) -> int:

#         return round(
#             (
#                 perf_counter()
#                 - started_at
#             )
#             * 1000
#         )

#     @classmethod
#     def _error_response(
#         cls,
#         *,
#         query_started: float,
#         timings: dict[str, int],
#         status: str,
#         intent: dict[str, Any],
#         answer: str,
#         data: Any = None,
#         warnings: (
#             list[str] | None
#         ) = None,
#     ) -> dict[str, Any]:

#         timings[
#             "total_ms"
#         ] = cls._elapsed_ms(
#             query_started
#         )

#         response: dict[
#             str,
#             Any,
#         ] = {

#             "status":
#                 status,

#             "intent":
#                 intent,

#             "answer":
#                 answer,

#             "warnings":
#                 warnings or [],

#             "timings":
#                 timings,

#             "response_time_ms":
#                 timings[
#                     "total_ms"
#                 ],

#             "response_time_seconds":
#                 round(
#                     timings[
#                         "total_ms"
#                     ]
#                     / 1000,
#                     2,
#                 ),
#         }

#         if data is not None:

#             response[
#                 "data"
#             ] = data

#         return response



from __future__ import annotations

from time import perf_counter
from typing import Any

from app.ai.answer_generator import GroqAnswerGenerator
from app.ai.groq_client import GroqIntentClient
from app.ai.snapshot_evidence import build_snapshot_evidence
from app.ai.snapshot_answer import try_generate_snapshot_answer
from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.mcp_client import AWSMCPClient
from app.providers.aws.query.multi_region_executor import AWSMultiRegionQueryExecutor
from app.providers.aws.query.read_only_validator import (
    AWSReadOnlyOperationValidator,
    UnsafeAWSOperationError,
)
from app.providers.aws.query.region_resolver import AWSQueryRegionResolver


class AWSQueryRouter:
    def __init__(self) -> None:
        self._intent_client = GroqIntentClient()
        self._validator = AWSReadOnlyOperationValidator()
        self._region_resolver = AWSQueryRegionResolver()
        self._executor = AWSMultiRegionQueryExecutor()
        self._answer_generator = GroqAnswerGenerator()

    async def execute(
        self,
        *,
        question: str,
        credentials: AWSCredentials | None,
        scan_result: dict[str, Any],
        conversation_context: str | None = None,
        selected_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        query_started = perf_counter()
        timings: dict[str, int] = {}

        # -------------------------------------------------
        # 1. NLP QUERY PLAN: snapshot vs live + optional AWS API plan
        # -------------------------------------------------
        stage_started = perf_counter()
        try:
            intent = self._intent_client.parse_aws_question(
                question,
                conversation_context=conversation_context,
                selected_context=selected_context,
            )
        except Exception as exc:
            timings["intent_ms"] = self._elapsed_ms(stage_started)
            return self._error_response(
                query_started=query_started,
                timings=timings,
                status="INTENT_PLANNING_FAILED",
                intent={},
                answer=f"Unable to understand the AWS question: {exc}",
            )

        timings["intent_ms"] = self._elapsed_ms(stage_started)
        intent_dict = intent.model_dump(mode="json")

        # -------------------------------------------------
        # 2. SAVED SNAPSHOT QUERY
        # -------------------------------------------------
        if not intent.requires_live_data:
            evidence = build_snapshot_evidence(
                scan_result=scan_result,
                selected_context=selected_context,
                intent=intent_dict,
            )

            # Common snapshot inventory questions are answered directly from
            # persisted evidence. This avoids unnecessary LLM token usage and
            # keeps simple list/count/cost/region queries deterministic.
            answer = try_generate_snapshot_answer(
                question=question,
                snapshot_evidence=evidence,
            )

            stage_started = perf_counter()
            try:
                if answer is None:
                    answer = self._answer_generator.generate_snapshot(
                        question=question,
                        snapshot_evidence=evidence,
                        conversation_context=conversation_context,
                    )
            except Exception as exc:
                timings["answer_ms"] = self._elapsed_ms(stage_started)
                return self._error_response(
                    query_started=query_started,
                    timings=timings,
                    status="ANSWER_GENERATION_FAILED",
                    intent=intent_dict,
                    answer=(
                        "The saved scan evidence was prepared, but snapshot answer "
                        f"formatting failed: {exc}"
                    ),
                    data=evidence,
                )

            timings["answer_ms"] = self._elapsed_ms(stage_started)
            timings["total_ms"] = self._elapsed_ms(query_started)
            return {
                "status": "SUCCESS",
                "source": "PERSISTED_DISCOVERY_SNAPSHOT",
                "scan_id": scan_result.get("scan_id"),
                "intent": intent_dict,
                "selected_context": dict(selected_context or {}),
                "answer": answer,
                "data": evidence,
                "warnings": scan_result.get("warnings") or [],
                "timings": timings,
                "response_time_ms": timings["total_ms"],
                "response_time_seconds": round(timings["total_ms"] / 1000, 2),
            }

        # -------------------------------------------------
        # 3. LIVE QUERY REQUIRES AN ACTIVE TRANSIENT AWS SESSION
        # -------------------------------------------------
        if credentials is None:
            return self._error_response(
                query_started=query_started,
                timings=timings,
                status="AWS_SESSION_REQUIRED",
                intent=intent_dict,
                answer=(
                    "This question requires current/live AWS data. The saved discovery "
                    "snapshot is still available, but reconnect the AWS account before "
                    "running this live query."
                ),
                data={
                    "source": "PERSISTED_DISCOVERY_SNAPSHOT",
                    "scan_id": scan_result.get("scan_id"),
                    "selected_context": dict(selected_context or {}),
                },
            )

        service = (intent.service or "").strip().lower()
        operation = (intent.operation or "").strip()

        if not service or not operation:
            return self._error_response(
                query_started=query_started,
                timings=timings,
                status="INVALID_LIVE_PLAN",
                intent=intent_dict,
                answer="The live AWS query plan did not resolve a service and read operation.",
            )

        # -------------------------------------------------
        # 4. READ-ONLY SAFETY VALIDATION
        # -------------------------------------------------
        try:
            self._validator.validate(service=service, operation=operation)
        except UnsafeAWSOperationError as exc:
            return self._error_response(
                query_started=query_started,
                timings=timings,
                status="OPERATION_BLOCKED",
                intent=intent_dict,
                answer=str(exc),
            )

        # -------------------------------------------------
        # 5. DISCOVERY EVIDENCE HELPS RESOLVE REGIONS
        # -------------------------------------------------
        detected_services = (
            scan_result.get("resources", {}).get("detected_services", [])
        )
        service_entry = next(
            (
                item
                for item in detected_services
                if str(item.get("service", "")).strip().lower() == service
            ),
            None,
        )

        target_regions = self._region_resolver.resolve(
            service=service,
            requested_region=intent.region,
            service_entry=service_entry,
            fallback_region=credentials.default_region,
        )

        if not target_regions:
            return self._error_response(
                query_started=query_started,
                timings=timings,
                status="NO_QUERY_REGION",
                intent=intent_dict,
                answer="No usable AWS Region could be resolved for this live query.",
            )

        # -------------------------------------------------
        # 6. OFFICIAL AWS MCP EXECUTION
        # -------------------------------------------------
        stage_started = perf_counter()
        try:
            async with AWSMCPClient(credentials) as mcp:
                execution = await self._executor.execute(
                    credentials=credentials,
                    service=service,
                    operation=operation,
                    regions=target_regions,
                    params=intent.get_params(),
                    mcp=mcp,
                )
        except Exception as exc:
            timings["aws_mcp_ms"] = self._elapsed_ms(stage_started)
            return self._error_response(
                query_started=query_started,
                timings=timings,
                status="AWS_MCP_EXECUTION_FAILED",
                intent=intent_dict,
                answer=f"AWS MCP query execution failed: {exc}",
            )

        timings["aws_mcp_ms"] = self._elapsed_ms(stage_started)
        execution_dict = execution.model_dump(mode="json")

        if not execution.successful_regions:
            return self._error_response(
                query_started=query_started,
                timings=timings,
                status="AWS_QUERY_FAILED",
                intent=intent_dict,
                answer="The AWS query failed in all target Regions.",
                data=execution_dict,
                warnings=execution.warnings,
            )

        # -------------------------------------------------
        # 7. LIVE ANSWER FORMATTING
        # -------------------------------------------------
        stage_started = perf_counter()
        try:
            answer = self._answer_generator.generate(
                question=question,
                intent=intent_dict,
                aws_result=execution_dict,
            )
        except Exception as exc:
            timings["answer_ms"] = self._elapsed_ms(stage_started)
            return self._error_response(
                query_started=query_started,
                timings=timings,
                status="ANSWER_GENERATION_FAILED",
                intent=intent_dict,
                answer=f"AWS data was retrieved, but answer formatting failed: {exc}",
                data=execution_dict,
                warnings=execution.warnings,
            )

        timings["answer_ms"] = self._elapsed_ms(stage_started)
        timings["total_ms"] = self._elapsed_ms(query_started)

        return {
            "status": "SUCCESS",
            "source": "LIVE_AWS_MCP",
            "scan_id": scan_result.get("scan_id"),
            "intent": intent_dict,
            "selected_context": dict(selected_context or {}),
            "answer": answer,
            "data": execution_dict,
            "warnings": execution.warnings,
            "timings": timings,
            "response_time_ms": timings["total_ms"],
            "response_time_seconds": round(timings["total_ms"] / 1000, 2),
        }

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return round((perf_counter() - started_at) * 1000)

    @classmethod
    def _error_response(
        cls,
        *,
        query_started: float,
        timings: dict[str, int],
        status: str,
        intent: dict[str, Any],
        answer: str,
        data: Any = None,
        warnings: list[str] | None = None,
    ) -> dict[str, Any]:
        timings["total_ms"] = cls._elapsed_ms(query_started)
        response: dict[str, Any] = {
            "status": status,
            "intent": intent,
            "answer": answer,
            "warnings": warnings or [],
            "timings": timings,
            "response_time_ms": timings["total_ms"],
            "response_time_seconds": round(timings["total_ms"] / 1000, 2),
        }
        if data is not None:
            response["data"] = data
        return response


