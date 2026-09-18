from app.providers.aws.collectors.ec2 import (
    EC2MCPCollector,
)
from app.providers.aws.collectors.iam import (
    IAMMCPCollector,
)
from app.providers.aws.collectors.rds import (
    RDSMCPCollector,
)
from app.providers.aws.collectors.registry import (
    AWSCollectorRegistry,
)
from app.providers.aws.collectors.s3 import (
    S3MCPCollector,
)


def create_collector_registry(
) -> AWSCollectorRegistry:

    return AWSCollectorRegistry(
        collectors=[
            EC2MCPCollector(),
            S3MCPCollector(),
            RDSMCPCollector(),
            IAMMCPCollector(),
        ]
    )