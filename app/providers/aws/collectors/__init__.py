# from app.providers.aws.collectors.ec2 import (
#     EC2MCPCollector,
# )
# from app.providers.aws.collectors.iam import (
#     IAMMCPCollector,
# )
# from app.providers.aws.collectors.rds import (
#     RDSMCPCollector,
# )
# from app.providers.aws.collectors.registry import (
#     AWSCollectorRegistry,
# )
# from app.providers.aws.collectors.s3 import (
#     S3MCPCollector,
# )


# def create_collector_registry(
# ) -> AWSCollectorRegistry:

#     return AWSCollectorRegistry(
#         collectors=[
#             EC2MCPCollector(),
#             S3MCPCollector(),
#             RDSMCPCollector(),
#             IAMMCPCollector(),
#         ]
#     )



from __future__ import annotations

from collections.abc import Iterable

from app.providers.aws.collectors.base import AWSMCPCollector
from app.providers.aws.collectors.registry import AWSCollectorRegistry


def create_collector_registry(
    collectors: Iterable[AWSMCPCollector] | None = None,
) -> AWSCollectorRegistry:
    """
    Create a runtime collector registry without pre-registering AWS services.

    Baseline AWS service discovery remains dynamic through AWS Resource
    Explorer via the AWS Managed MCP Server. Optional deep collectors may be
    supplied explicitly at runtime when required.
    """

    return AWSCollectorRegistry(collectors=collectors)


__all__ = [
    "AWSCollectorRegistry",
    "AWSMCPCollector",
    "create_collector_registry",
]


