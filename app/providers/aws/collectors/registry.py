from __future__ import annotations

from app.providers.aws.collectors.base import AWSMCPCollector


class AWSCollectorRegistry:
    def __init__(
        self,
        collectors: list[AWSMCPCollector],
    ) -> None:
        self._collectors = {
            collector.service_name.lower(): collector
            for collector in collectors
        }

    def get(
        self,
        service_name: str,
    ) -> AWSMCPCollector | None:
        return self._collectors.get(service_name.lower())

    def available_services(self) -> list[str]:
        return sorted(self._collectors.keys())
