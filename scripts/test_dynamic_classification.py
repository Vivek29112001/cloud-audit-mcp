from app.providers.aws.classification import AWSInfrastructureClassificationService
from app.providers.aws.models import AWSBillingDiscoveryResult,AWSBillingRegionCost,AWSBillingServiceCost,AWSDetectedService,AWSRegion,AWSRegionDiscoveryResult,AWSResource,AWSResourceDiscoveryResult

def main():
    svc=AWSInfrastructureClassificationService()
    for billing,service in [("Amazon Elastic Compute Cloud - Compute","ec2"),("Amazon Simple Storage Service","s3"),("Amazon Relational Database Service","rds"),("AWS Key Management Service","kms")]:
        m=svc._best_service_match(billing_name=billing,discovered_services=[service]);assert m and m[0]==service
    resources=AWSResourceDiscoveryResult(total_resources=3,used_regions=["ap-south-1"],detected_services=[AWSDetectedService(service="ec2",resource_count=1,regions=["ap-south-1"]),AWSDetectedService(service="kms",resource_count=1,regions=["ap-south-1"]),AWSDetectedService(service="s3",resource_count=1,regions=["ap-south-1"])],resources=[AWSResource(arn="arn:aws:ec2:ap-south-1:123:instance/i-12345678",resource_id="i-12345678",service="ec2",region="ap-south-1",properties=[{"Kms":"arn:aws:kms:ap-south-1:123:key/key-12345678"}]),AWSResource(arn="arn:aws:kms:ap-south-1:123:key/key-12345678",resource_id="key-12345678",service="kms",region="ap-south-1"),AWSResource(arn="arn:aws:s3:::bucket-a",resource_id="bucket-a",service="s3",region="ap-south-1")])
    regions=AWSRegionDiscoveryResult(total_regions=2,enabled_regions=2,disabled_regions=0,regions=[AWSRegion(region_name="ap-south-1",enabled=True),AWSRegion(region_name="us-east-1",enabled=True)])
    billing=AWSBillingDiscoveryResult(available=True,period_start="2026-09-01",period_end_exclusive="2026-09-23",total_cost=12,currency="USD",service_costs=[AWSBillingServiceCost(billing_service="Amazon Elastic Compute Cloud - Compute",amount=10),AWSBillingServiceCost(billing_service="Amazon Simple Storage Service",amount=0),AWSBillingServiceCost(billing_service="AWS Cost Explorer",amount=2)],region_costs=[AWSBillingRegionCost(region="ap-south-1",amount=10)])
    c=svc.classify(regions=regions,resources=resources,billing=billing)
    assert [x.key for x in c.primary_paid_services]==["ec2"]
    assert [x.key for x in c.zero_cost_services]==["s3"]
    assert [x.key for x in c.supporting_services]==["kms"]
    assert c.billing_only_services[0].billing_services==["AWS Cost Explorer"]
    print("dynamic classification tests passed")
if __name__=="__main__":main()
