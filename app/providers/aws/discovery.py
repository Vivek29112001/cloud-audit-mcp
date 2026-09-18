from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.exceptions import AWSMCPExecutionError
from app.providers.aws.mcp_client import AWSMCPClient
from app.providers.aws.models import (
    AWSDetectedService,
    AWSResource,
    AWSResourceDiscoveryResult,
)
from app.providers.aws.result_parser import (
    extract_mcp_result,
)
from app.providers.aws.mcp_scripts.resource_discovery import (
    build_resource_discovery_script,
)


class AWSResourceDiscoveryService:
    """
    Lightweight Resource Explorer discovery.

    Important:
    - Uses the already-open MCP session when provided.
    - Searches Regions with bounded concurrency instead of sequentially.
    - Does not perform service-specific deep scanning.
    """

    MAX_CONCURRENT_REGIONS = 5

    async def discover_resources(
        self,
        credentials: AWSCredentials | None = None,
        enabled_regions: list[str] | None = None,
        *,
        mcp: AWSMCPClient | None = None,
    ) -> AWSResourceDiscoveryResult:

        enabled_regions = (
            enabled_regions
            or []
        )

        if not enabled_regions:
            return AWSResourceDiscoveryResult(
                total_resources=0,
                used_regions=[],
                detected_services=[],
                resources=[],
                warnings=[
                    "No enabled AWS Regions were supplied."
                ],
            )

        if mcp is None:
            if credentials is None:
                raise ValueError(
                    "Either credentials or an open AWSMCPClient "
                    "session is required."
                )

            async with AWSMCPClient(
                credentials
            ) as session:
                return await self.discover_resources(
                    enabled_regions=enabled_regions,
                    mcp=session,
                )

        semaphore = asyncio.Semaphore(
            self.MAX_CONCURRENT_REGIONS
        )

        async def discover_region(
            region: str,
        ) -> tuple[
            str,
            list[AWSResource] | None,
            Exception | None,
        ]:
            async with semaphore:
                try:
                    resources = (
                        await self._discover_region(
                            client=mcp,
                            region=region,
                        )
                    )

                    return (
                        region,
                        resources,
                        None,
                    )

                except Exception as exc:
                    return (
                        region,
                        None,
                        exc,
                    )

        regional_results = await asyncio.gather(
            *[
                discover_region(
                    region
                )
                for region
                in enabled_regions
            ]
        )

        all_resources: list[
            AWSResource
        ] = []

        warnings: list[str] = []

        for (
            region,
            regional_resources,
            error,
        ) in regional_results:

            if error is not None:
                warnings.append(
                    "Resource discovery failed "
                    f"for {region}: {error}"
                )
                continue

            if regional_resources:
                all_resources.extend(
                    regional_resources
                )

        all_resources = (
            self._deduplicate_resources(
                all_resources
            )
        )

        used_regions = sorted(
            {
                resource.region
                for resource
                in all_resources
                if resource.region
                and resource.region != "global"
            }
        )

        detected_services = (
            self._build_service_summary(
                all_resources
            )
        )

        return AWSResourceDiscoveryResult(
            total_resources=len(
                all_resources
            ),
            used_regions=used_regions,
            detected_services=(
                detected_services
            ),
            resources=all_resources,
            warnings=warnings,
        )

    async def _discover_region(
        self,
        client: AWSMCPClient,
        region: str,
    ) -> list[AWSResource]:

        script = (
            build_resource_discovery_script(
                region=region
            )
        )

        try:
            response = (
                await client
                .run_aws_script(
                    script
                )
            )

        except Exception as exc:
            raise AWSMCPExecutionError(
                "Resource Explorer search "
                f"failed in {region}: {exc}"
            ) from exc

        parsed = extract_mcp_result(
            response
        )

        raw_resources = (
            self._find_resources(
                parsed
            )
        )

        result: list[
            AWSResource
        ] = []

        for item in raw_resources:

            arn = item.get(
                "Arn"
            )

            result.append(
                AWSResource(
                    arn=arn,
                    resource_id=(
                        self._resource_id_from_arn(
                            arn
                        )
                    ),
                    resource_type=(
                        item.get(
                            "ResourceType"
                        )
                    ),
                    service=(
                        item.get(
                            "Service"
                        )
                    ),
                    region=(
                        item.get(
                            "Region"
                        )
                        or region
                    ),
                    owning_account_id=(
                        item.get(
                            "OwningAccountId"
                        )
                    ),
                    properties=(
                        item.get(
                            "Properties",
                            [],
                        )
                    ),
                )
            )

        return result

    @staticmethod
    def _find_resources(
        value: Any,
    ) -> list[dict[str, Any]]:

        if isinstance(
            value,
            dict,
        ):
            resources = value.get(
                "Resources"
            )

            if isinstance(
                resources,
                list,
            ):
                return resources

            for child in value.values():
                found = (
                    AWSResourceDiscoveryService
                    ._find_resources(
                        child
                    )
                )

                if found:
                    return found

        elif isinstance(
            value,
            list,
        ):
            for child in value:
                found = (
                    AWSResourceDiscoveryService
                    ._find_resources(
                        child
                    )
                )

                if found:
                    return found

        return []

    @staticmethod
    def _resource_id_from_arn(
        arn: str | None,
    ) -> str | None:

        if not arn:
            return None

        resource_part = arn.split(
            ":",
            maxsplit=5,
        )

        if len(
            resource_part
        ) < 6:
            return arn

        value = resource_part[5]

        if "/" in value:
            return value.rsplit(
                "/",
                maxsplit=1,
            )[-1]

        if ":" in value:
            return value.rsplit(
                ":",
                maxsplit=1,
            )[-1]

        return value

    @staticmethod
    def _deduplicate_resources(
        resources: list[
            AWSResource
        ],
    ) -> list[AWSResource]:

        unique: dict[
            str,
            AWSResource,
        ] = {}

        anonymous: list[
            AWSResource
        ] = []

        for resource in resources:

            if resource.arn:
                unique[
                    resource.arn
                ] = resource

            else:
                anonymous.append(
                    resource
                )

        return (
            list(
                unique.values()
            )
            + anonymous
        )

    @staticmethod
    def _build_service_summary(
        resources: list[
            AWSResource
        ],
    ) -> list[
        AWSDetectedService
    ]:

        counts: dict[
            str,
            int,
        ] = defaultdict(int)

        regions: dict[
            str,
            set[str],
        ] = defaultdict(set)

        for resource in resources:

            if not resource.service:
                continue

            service = (
                resource.service
                .strip()
                .lower()
            )

            counts[
                service
            ] += 1

            if resource.region:
                regions[
                    service
                ].add(
                    resource.region
                )

        result = [
            AWSDetectedService(
                service=service,
                resource_count=count,
                regions=sorted(
                    regions[
                        service
                    ]
                ),
            )
            for service, count
            in counts.items()
        ]

        result.sort(
            key=lambda item: (
                -item.resource_count,
                item.service,
            )
        )

        return result
