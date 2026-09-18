from __future__ import annotations

from time import perf_counter
from typing import Any

from app.ai.answer_generator import (
    GroqAnswerGenerator,
)
from app.ai.groq_client import (
    GroqIntentClient,
)
from app.providers.aws.credentials import (
    AWSCredentials,
)
from app.providers.aws.mcp_client import (
    AWSMCPClient,
)
from app.providers.aws.query.multi_region_executor import (
    AWSMultiRegionQueryExecutor,
)
from app.providers.aws.query.read_only_validator import (
    AWSReadOnlyOperationValidator,
    UnsafeAWSOperationError,
)
from app.providers.aws.query.region_resolver import (
    AWSQueryRegionResolver,
)


class AWSQueryRouter:

    ACCOUNT_LEVEL_SERVICES = {
        "iam",
        "organizations",
        "route53",
        "cloudfront",
    }

    def __init__(self) -> None:

        self._intent_client = (
            GroqIntentClient()
        )

        self._validator = (
            AWSReadOnlyOperationValidator()
        )

        self._region_resolver = (
            AWSQueryRegionResolver()
        )

        self._executor = (
            AWSMultiRegionQueryExecutor()
        )

        self._answer_generator = (
            GroqAnswerGenerator()
        )

    async def execute(
        self,
        *,
        question: str,
        credentials: AWSCredentials,
        scan_result: dict[str, Any],
    ) -> dict[str, Any]:

        #
        # Total query timer
        #
        query_started = perf_counter()

        timings: dict[str, int] = {}

        #
        # -------------------------------------------------
        # 1. NLP QUERY PLAN
        # -------------------------------------------------
        #

        stage_started = perf_counter()

        intent = (
            self._intent_client
            .parse_aws_question(
                question
            )
        )

        timings["intent_ms"] = (
            self._elapsed_ms(
                stage_started
            )
        )

        service = (
            intent.service
            .strip()
            .lower()
        )

        operation = (
            intent.operation
            .strip()
        )

        #
        # -------------------------------------------------
        # 2. READ-ONLY SAFETY VALIDATION
        # -------------------------------------------------
        #

        try:

            self._validator.validate(
                service=service,
                operation=operation,
            )

        except UnsafeAWSOperationError as exc:

            return self._error_response(
                query_started=query_started,
                timings=timings,
                status="OPERATION_BLOCKED",
                intent=intent.model_dump(
                    mode="json"
                ),
                answer=str(exc),
            )

        #
        # -------------------------------------------------
        # 3. CHECK BASELINE SERVICE DISCOVERY
        # -------------------------------------------------
        #

        detected_services = (
            scan_result
            .get(
                "resources",
                {}
            )
            .get(
                "detected_services",
                []
            )
        )

        service_entry = next(
            (
                item
                for item
                in detected_services
                if item.get(
                    "service",
                    ""
                ).lower()
                == service
            ),
            None,
        )

        if (
            not service_entry
            and service
            not in self.ACCOUNT_LEVEL_SERVICES
        ):

            return self._error_response(
                query_started=query_started,
                timings=timings,
                status="SERVICE_NOT_DETECTED",
                intent=intent.model_dump(
                    mode="json"
                ),
                answer=(
                    f"No {service.upper()} "
                    "resources were detected "
                    "in the latest discovery scan."
                ),
            )

        #
        # -------------------------------------------------
        # 4. RESOLVE TARGET REGIONS
        # -------------------------------------------------
        #

        target_regions = (
            self._region_resolver
            .resolve(
                service=service,
                requested_region=(
                    intent.region
                ),
                service_entry=(
                    service_entry
                ),
            )
        )

        if not target_regions:

            return self._error_response(
                query_started=query_started,
                timings=timings,
                status="NO_QUERY_REGION",
                intent=intent.model_dump(
                    mode="json"
                ),
                answer=(
                    "The query service was detected, "
                    "but no usable AWS Region could "
                    "be resolved."
                ),
            )

        #
        # -------------------------------------------------
        # 5. OFFICIAL AWS MCP EXECUTION
        #
        # Important:
        # Open MCP ONCE for this complete NLP query.
        #
        # All Region queries reuse this same session.
        # -------------------------------------------------
        #

        stage_started = perf_counter()

        try:

            async with AWSMCPClient(
                credentials
            ) as mcp:

                execution = (
                    await self._executor
                    .execute(
                        credentials=credentials,
                        service=service,
                        operation=operation,
                        regions=target_regions,

                        # Use decoded params_json
                        params=intent.get_params(),

                        # Reuse this ONE MCP session
                        mcp=mcp,
                    )
                )

        except Exception as exc:

            timings["aws_mcp_ms"] = (
                self._elapsed_ms(
                    stage_started
                )
            )

            return self._error_response(
                query_started=query_started,
                timings=timings,
                status="AWS_MCP_EXECUTION_FAILED",
                intent=intent.model_dump(
                    mode="json"
                ),
                answer=(
                    "AWS MCP query execution failed: "
                    f"{exc}"
                ),
            )

        timings["aws_mcp_ms"] = (
            self._elapsed_ms(
                stage_started
            )
        )

        execution_dict = (
            execution.model_dump(
                mode="json"
            )
        )

        if not execution.successful_regions:

            return self._error_response(
                query_started=query_started,
                timings=timings,
                status="AWS_QUERY_FAILED",
                intent=intent.model_dump(
                    mode="json"
                ),
                answer=(
                    "The AWS query failed in "
                    "all target Regions."
                ),
                data=execution_dict,
                warnings=execution.warnings,
            )

        #
        # -------------------------------------------------
        # 6. GROQ ANSWER FORMATTING
        # -------------------------------------------------
        #

        stage_started = perf_counter()

        answer = (
            self._answer_generator
            .generate(
                question=question,

                intent=(
                    intent.model_dump(
                        mode="json"
                    )
                ),

                aws_result=(
                    execution_dict
                ),
            )
        )

        timings["answer_ms"] = (
            self._elapsed_ms(
                stage_started
            )
        )

        #
        # -------------------------------------------------
        # 7. TOTAL RESPONSE TIME
        # -------------------------------------------------
        #

        timings["total_ms"] = (
            self._elapsed_ms(
                query_started
            )
        )

        return {
            "status": "SUCCESS",

            "intent": (
                intent.model_dump(
                    mode="json"
                )
            ),

            "answer": answer,

            "data": execution_dict,

            "warnings": (
                execution.warnings
            ),

            #
            # Developer timing breakdown
            #
            "timings": timings,

            #
            # Easy frontend display
            #
            "response_time_ms": (
                timings["total_ms"]
            ),

            "response_time_seconds": round(
                timings["total_ms"]
                / 1000,
                2,
            ),
        }

    @staticmethod
    def _elapsed_ms(
        started_at: float,
    ) -> int:

        return round(
            (
                perf_counter()
                - started_at
            )
            * 1000
        )

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

        timings["total_ms"] = (
            cls._elapsed_ms(
                query_started
            )
        )

        response = {
            "status": status,

            "intent": intent,

            "answer": answer,

            "warnings": (
                warnings or []
            ),

            "timings": timings,

            "response_time_ms": (
                timings["total_ms"]
            ),

            "response_time_seconds": round(
                timings["total_ms"]
                / 1000,
                2,
            ),
        }

        if data is not None:
            response["data"] = data

        return response