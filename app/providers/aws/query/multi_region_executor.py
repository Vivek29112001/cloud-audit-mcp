from __future__ import annotations

import asyncio
from typing import Any

from app.providers.aws.credentials import (
    AWSCredentials,
)
from app.providers.aws.mcp_client import (
    AWSMCPClient,
)
from app.providers.aws.query.generic_executor import (
    AWSGenericQueryExecutor,
)
from app.providers.aws.query.models import (
    AWSQueryExecutionResult,
    AWSRegionalQueryResult,
)


class AWSMultiRegionQueryExecutor:

    MAX_CONCURRENT_REGIONS = 5

    def __init__(self) -> None:

        self._executor = (
            AWSGenericQueryExecutor()
        )

    async def execute(
        self,
        *,
        credentials: AWSCredentials,
        service: str,
        operation: str,
        regions: list[str],
        params: dict[str, Any] | None = None,
        mcp: AWSMCPClient | None = None,
    ) -> AWSQueryExecutionResult:

        unique_regions = sorted(
            set(regions)
        )

        #
        # Standalone compatibility:
        # if caller did not provide MCP,
        # open ONE session here.
        #
        if mcp is None:

            async with AWSMCPClient(
                credentials
            ) as session:

                return await self.execute(
                    credentials=credentials,
                    service=service,
                    operation=operation,
                    regions=unique_regions,
                    params=params,
                    mcp=session,
                )

        semaphore = asyncio.Semaphore(
            self.MAX_CONCURRENT_REGIONS
        )

        async def query_region(
            region: str,
        ):

            async with semaphore:

                return await (
                    self._executor.execute(
                        service=service,
                        operation=operation,
                        region=region,
                        params=params,

                        # SAME MCP session
                        mcp=mcp,
                    )
                )

        raw_results = await asyncio.gather(
            *[
                query_region(region)
                for region
                in unique_regions
            ],
            return_exceptions=True,
        )

        results: list[
            AWSRegionalQueryResult
        ] = []

        successful_regions: list[str] = []
        failed_regions: list[str] = []
        warnings: list[str] = []

        for (
            region,
            raw_result,
        ) in zip(
            unique_regions,
            raw_results,
        ):

            if isinstance(
                raw_result,
                Exception,
            ):

                failed_regions.append(
                    region
                )

                warnings.append(
                    f"{region}: "
                    f"{raw_result}"
                )

                results.append(
                    AWSRegionalQueryResult(
                        region=region,
                        success=False,
                        error=str(
                            raw_result
                        ),
                    )
                )

                continue

            successful_regions.append(
                region
            )

            results.append(
                AWSRegionalQueryResult(
                    region=region,
                    success=True,

                    pages=raw_result.get(
                        "page_count",
                        1,
                    ),

                    data=raw_result.get(
                        "pages",
                        [],
                    ),
                )
            )

        return AWSQueryExecutionResult(
            service=service,
            operation=operation,
            regions=unique_regions,

            successful_regions=(
                successful_regions
            ),

            failed_regions=(
                failed_regions
            ),

            results=results,

            warnings=warnings,
        )