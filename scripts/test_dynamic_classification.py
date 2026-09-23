from app.providers.aws.classification import AWSInfrastructureClassificationService
from app.providers.aws.models import (
    AWSBillingDiscoveryResult,
    AWSBillingRegionCost,
    AWSBillingServiceCost,
    AWSDetectedService,
    AWSRegion,
    AWSRegionDiscoveryResult,
    AWSResource,
    AWSResourceDiscoveryResult,
)


def main() -> None:
    service = AWSInfrastructureClassificationService()

    alias_cases = {
        "Amazon Elastic Compute Cloud - Compute": "ec2",
        "EC2 - Other": "ec2",
        "Amazon Simple Storage Service": "s3",
        "Amazon Relational Database Service": "rds",
        "AWS Key Management Service": "kms",
        "AmazonCloudWatch": "cloudwatch",
        "Amazon Elastic Load Balancing": "elasticloadbalancing",
    }

    for billing_name, discovered_name in alias_cases.items():
        match = service._best_service_match(
            billing_name=billing_name,
            discovered_services=[discovered_name],
        )
        assert match is not None, (billing_name, discovered_name)
        assert match[0] == discovered_name
        assert match[2] >= 0.82

    resources = AWSResourceDiscoveryResult(
        total_resources=3,
        used_regions=["ap-south-1"],
        detected_services=[
            AWSDetectedService(
                service="ec2",
                resource_count=1,
                regions=["ap-south-1"],
            ),
            AWSDetectedService(
                service="kms",
                resource_count=1,
                regions=["ap-south-1"],
            ),
            AWSDetectedService(
                service="s3",
                resource_count=1,
                regions=["ap-south-1"],
            ),
        ],
        resources=[
            AWSResource(
                arn="arn:aws:ec2:ap-south-1:123456789012:instance/i-12345678",
                resource_id="i-12345678",
                service="ec2",
                region="ap-south-1",
                properties=[
                    {
                        "KmsKey": (
                            "arn:aws:kms:ap-south-1:123456789012:"
                            "key/key-12345678"
                        )
                    }
                ],
            ),
            AWSResource(
                arn=(
                    "arn:aws:kms:ap-south-1:123456789012:"
                    "key/key-12345678"
                ),
                resource_id="key-12345678",
                service="kms",
                region="ap-south-1",
            ),
            AWSResource(
                arn="arn:aws:s3:::sample-bucket",
                resource_id="sample-bucket",
                service="s3",
                region="ap-south-1",
            ),
        ],
    )

    regions = AWSRegionDiscoveryResult(
        total_regions=2,
        enabled_regions=2,
        disabled_regions=0,
        regions=[
            AWSRegion(region_name="ap-south-1", enabled=True),
            AWSRegion(region_name="us-east-1", enabled=True),
        ],
    )

    billing = AWSBillingDiscoveryResult(
        available=True,
        period_start="2026-09-01",
        period_end_exclusive="2026-09-23",
        currency="USD",
        total_cost=10.0,
        service_costs=[
            AWSBillingServiceCost(
                billing_service="Amazon Elastic Compute Cloud - Compute",
                amount=10.0,
            )
        ],
        region_costs=[
            AWSBillingRegionCost(
                region="ap-south-1",
                amount=10.0,
            )
        ],
    )

    classified = service.classify(
        regions=regions,
        resources=resources,
        billing=billing,
    )

    assert [item.key for item in classified.primary_paid_services] == ["ec2"]
    assert [item.key for item in classified.supporting_services] == ["kms"]
    assert [item.key for item in classified.discovered_unbilled_services] == ["s3"]
    assert classified.paid_regions[0].region == "ap-south-1"
    assert classified.enabled_unused_regions[0].region == "us-east-1"
    assert len(classified.relationships) == 1

    print("dynamic classification tests passed")


if __name__ == "__main__":
    main()
