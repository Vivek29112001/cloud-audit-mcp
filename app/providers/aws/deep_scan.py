from app.providers.aws.collectors import create_collector_registry
from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.models import (
    AWSDeepScanResult,
    AWSDetectedService,
)


class AWSDeepScanService:
    def __init__(self) -> None:
        self._registry = create_collector_registry()

    async def scan(
        self,
        credentials: AWSCredentials,
        detected_services: list[AWSDetectedService],
    ) -> AWSDeepScanResult:
        results: dict[str, object] = {}
        warnings: list[str] = []

        for service in detected_services:
            service_name = service.service.strip().lower()
            collector = self._registry.get(service_name)

            if not collector:
                warnings.append(
                    f"No deep collector is available yet for '{service_name}'."
                )
                continue

            regions = sorted(
                {
                    region
                    for region in service.regions
                    if region and region != "global"
                }
            )

            if not regions:
                warnings.append(
                    f"Service '{service_name}' was detected, but no regional "
                    "scope was available for its deep collector."
                )
                continue

            try:
                results[service_name] = await collector.collect(
                    credentials=credentials,
                    regions=regions,
                )
            except Exception as exc:
                warnings.append(
                    f"Deep collector failed for '{service_name}': {exc}"
                )

        return AWSDeepScanResult(
            services=results,
            warnings=warnings,
        )
