from app.providers.aws.collectors.ec2 import EC2DeepCollector
from app.providers.aws.collectors.registry import AWSCollectorRegistry


def create_collector_registry() -> AWSCollectorRegistry:
    return AWSCollectorRegistry(
        collectors=[
            EC2DeepCollector(),
        ]
    )
