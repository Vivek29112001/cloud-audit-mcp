from __future__ import annotations

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


class AWSResourceDiscoveryService:

    async def discover_resources(
        self,
        credentials: AWSCredentials,
        enabled_regions: list[str],
    ) -> AWSResourceDiscoveryResult:

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

        client = AWSMCPClient(credentials)

        all_resources: list[AWSResource] = []
        warnings: list[str] = []

        for region in enabled_regions:

            try:
                regional_resources = (
                    await self._discover_region(
                        client=client,
                        region=region,
                    )
                )

                all_resources.extend(
                    regional_resources
                )

            except Exception as exc:
                warnings.append(
                    f"Resource discovery failed "
                    f"for {region}: {exc}"
                )

        all_resources = (
            self._deduplicate_resources(
                all_resources
            )
        )

        used_regions = sorted(
            {
                resource.region
                for resource in all_resources
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

        script = f"""
region = {region!r}

resources = []

next_token = None

while True:

    params = {{
        "QueryString": "",
        "MaxResults": 1000
    }}

    if next_token:
        params["NextToken"] = next_token

    response = await call_boto3(
        service_name="resource-explorer-2",
        operation_name="Search",
        region_name=region,
        params=params
    )

    for item in response.get(
        "Resources",
        []
    ):
        resources.append({{
            "Arn": item.get("Arn"),
            "Region": item.get("Region"),
            "ResourceType": item.get(
                "ResourceType"
            ),
            "Service": item.get(
                "Service"
            ),
            "OwningAccountId": item.get(
                "OwningAccountId"
            ),
            "Properties": item.get(
                "Properties",
                []
            ),
        }})

    next_token = response.get(
        "NextToken"
    )

    if not next_token:
        break

result = {{
    "Resources": resources
}}

result
"""

        try:

            response = (
                await client
                .execute_aws_script(script)
            )

        except Exception as exc:

            raise AWSMCPExecutionError(
                f"Resource Explorer search "
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

        result: list[AWSResource] = []

        for item in raw_resources:

            arn = item.get("Arn")

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

        if isinstance(value, dict):

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
                    ._find_resources(child)
                )

                if found:
                    return found

        elif isinstance(value, list):

            for child in value:

                found = (
                    AWSResourceDiscoveryService
                    ._find_resources(child)
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

        if len(resource_part) < 6:
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
        resources: list[AWSResource],
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
            list(unique.values())
            + anonymous
        )

    @staticmethod
    def _build_service_summary(
        resources: list[AWSResource],
    ) -> list[AWSDetectedService]:

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

            counts[service] += 1

            if resource.region:
                regions[service].add(
                    resource.region
                )

        result = [
            AWSDetectedService(
                service=service,
                resource_count=count,
                regions=sorted(
                    regions[service]
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