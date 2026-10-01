# from __future__ import annotations

# from app.providers.aws.collectors.base import AWSMCPCollector


# class AWSCollectorRegistry:
#     def __init__(
#         self,
#         collectors: list[AWSMCPCollector],
#     ) -> None:
#         self._collectors = {
#             collector.service_name.lower(): collector
#             for collector in collectors
#         }

#     def get(
#         self,
#         service_name: str,
#     ) -> AWSMCPCollector | None:
#         return self._collectors.get(service_name.lower())

#     def available_services(self) -> list[str]:
#         return sorted(self._collectors.keys())



from __future__ import annotations

from collections.abc import Iterable

from app.providers.aws.collectors.base import AWSMCPCollector


class AWSCollectorRegistry:
    """
    Runtime registry for optional service-specific deep collectors.

    The registry itself contains no predefined AWS service catalogue.
    Baseline service discovery should continue to come from AWS Resource
    Explorer through MCP.
    """

    def __init__(
        self,
        collectors: Iterable[AWSMCPCollector] | None = None,
    ) -> None:
        self._collectors: dict[str, AWSMCPCollector] = {}

        if collectors:
            self.register_many(collectors)

    @staticmethod
    def _normalize_service_name(service_name: str) -> str:
        return str(service_name or "").strip().lower()

    def register(self, collector: AWSMCPCollector) -> None:
        """Register a service-specific collector at runtime."""

        service_name = self._normalize_service_name(
            collector.service_name
        )

        if not service_name:
            raise ValueError("Collector service_name cannot be empty.")

        self._collectors[service_name] = collector

    def register_many(
        self,
        collectors: Iterable[AWSMCPCollector],
    ) -> None:
        for collector in collectors:
            self.register(collector)

    def unregister(self, service_name: str) -> bool:
        normalized = self._normalize_service_name(service_name)

        if not normalized:
            return False

        return self._collectors.pop(normalized, None) is not None

    def get(
        self,
        service_name: str,
    ) -> AWSMCPCollector | None:
        normalized = self._normalize_service_name(service_name)

        if not normalized:
            return None

        return self._collectors.get(normalized)

    def contains(self, service_name: str) -> bool:
        normalized = self._normalize_service_name(service_name)

        if not normalized:
            return False

        return normalized in self._collectors

    def available_services(self) -> list[str]:
        """Return only collectors that were registered at runtime."""
        return sorted(self._collectors.keys())

    def clear(self) -> None:
        self._collectors.clear()

    def __len__(self) -> int:
        return len(self._collectors)

    def __contains__(self, service_name: str) -> bool:
        return self.contains(service_name)


