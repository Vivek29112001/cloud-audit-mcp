# from datetime import datetime, timezone
# from typing import Any
# from pydantic import BaseModel,Field


# class AWSIdentity(BaseModel):
#     account_id: str
#     arn: str
#     user_id: str

#     provider: str = "AWS"
#     connection_status: str = "VERIFIED"


# class AWSRegion(BaseModel):
#     region_name: str
#     endpoint: str | None = None
#     opt_in_status: str | None = None
#     enabled: bool


# class AWSRegionDiscoveryResult(BaseModel):
#     total_regions: int
#     enabled_regions: int
#     disabled_regions: int
#     regions: list[AWSRegion]


# class AWSAvailabilityZone(BaseModel):
#     zone_name: str
#     zone_id: str | None = None
#     region_name: str

#     state: str | None = None
#     zone_type: str | None = None
#     opt_in_status: str | None = None


# class AWSZoneDiscoveryResult(BaseModel):
#     total_zones: int
#     zones: list[AWSAvailabilityZone]

# class AWSResource(BaseModel):
#     arn : str | None = None
    
#     resource_id: str | None = None
#     resource_type: str | None = None
    
#     service: str | None = None
    
#     region: str | None = None
    
#     owning_account_id: str | None = None
    
#     properties: list[dict[str, Any]] = Field(
#         default_factory=list
#     )
    
# class AWSDetectedService(BaseModel):
#     service : str
#     resource_count: int
#     regions: list[str] = Field(
#         default_factory=list
#     )
    
# class AWSResourceDiscoveryResult(BaseModel):
#     total_resources: int
#     used_regions: list[str]
#     detected_services: list[AWSDetectedService]
#     resources: list[AWSResource]
#     warnings : list[str] = Field(
#         default_factory=list
#     )


# class AWSBillingServiceCost(BaseModel):
#     billing_service: str
#     amount: float
#     unit: str = "USD"


# class AWSBillingComponent(BaseModel):
#     billing_service: str
#     usage_type: str
#     amount: float
#     unit: str = "USD"


# class AWSBillingRegionCost(BaseModel):
#     region: str
#     amount: float
#     unit: str = "USD"


# class AWSBillingDiscoveryResult(BaseModel):
#     available: bool = False
#     period_start: str
#     period_end_exclusive: str
#     metric: str = "UnblendedCost"
#     currency: str = "USD"
#     total_cost: float = 0.0
#     service_costs: list[AWSBillingServiceCost] = Field(default_factory=list)
#     components: list[AWSBillingComponent] = Field(default_factory=list)
#     region_costs: list[AWSBillingRegionCost] = Field(default_factory=list)
#     warnings: list[str] = Field(default_factory=list)


# class AWSResourceRelationship(BaseModel):
#     source_arn: str | None = None
#     source_resource_id: str | None = None
#     source_service: str | None = None
#     target_arn: str | None = None
#     target_resource_id: str | None = None
#     target_service: str | None = None
#     evidence: str


# class AWSClassifiedService(BaseModel):
#     key: str
#     category: str
#     paid: bool
#     billing_amount: float = 0.0
#     currency: str = "USD"
#     billing_services: list[str] = Field(default_factory=list)
#     billing_components: list[AWSBillingComponent] = Field(default_factory=list)
#     discovered_service: str | None = None
#     resource_count: int = 0
#     regions: list[str] = Field(default_factory=list)
#     related_primary_services: list[str] = Field(default_factory=list)
#     billing_match_method: str | None = None
#     billing_match_confidence: float | None = None


# class AWSClassifiedRegion(BaseModel):
#     region: str
#     category: str
#     billing_amount: float = 0.0
#     currency: str = "USD"
#     resource_count: int = 0
#     enabled: bool = False


# class AWSInfrastructureClassificationResult(BaseModel):
#     billing_available: bool = False
#     primary_paid_services: list[AWSClassifiedService] = Field(default_factory=list)
#     supporting_services: list[AWSClassifiedService] = Field(default_factory=list)
#     discovered_unbilled_services: list[AWSClassifiedService] = Field(default_factory=list)
#     non_positive_billing_services: list[AWSClassifiedService] = Field(default_factory=list)
#     paid_regions: list[AWSClassifiedRegion] = Field(default_factory=list)
#     used_unbilled_regions: list[AWSClassifiedRegion] = Field(default_factory=list)
#     enabled_unused_regions: list[AWSClassifiedRegion] = Field(default_factory=list)
#     billed_only_regions: list[AWSClassifiedRegion] = Field(default_factory=list)
#     relationships: list[AWSResourceRelationship] = Field(default_factory=list)
#     warnings: list[str] = Field(default_factory=list)


# class AWSSecurityGroupRule(BaseModel):
#     protocol : str | None = None
#     from_port: int | None = None
#     to_port: int | None = None
    
#     ipv4_ranges: list[str] = Field(
#         default_factory=list
#     )
    
#     ipv6_ranges: list[str] = Field(
#         default_factory=list
#     )
    

# class AWSSecurityGroup(BaseModel):
#     group_id: str

#     group_name: str | None = None

#     description: str | None = None

#     vpc_id: str | None = None
    
#     region: str | None = None

#     ingress_rules: list[
#         AWSSecurityGroupRule
#     ] = Field(default_factory=list)

#     egress_rules: list[
#         AWSSecurityGroupRule
#     ] = Field(default_factory=list)


# class AWSEBSVolume(BaseModel):
#     volume_id: str
    
#     region: str | None = None

#     size_gb: int | None = None

#     volume_type: str | None = None

#     encrypted: bool | None = None

#     kms_key_id: str | None = None

#     state: str | None = None

#     availability_zone: str | None = None


# class AWSEC2Instance(BaseModel):
#     instance_id: str

#     name: str | None = None

#     instance_type: str | None = None

#     state: str | None = None

#     region: str

#     availability_zone: str | None = None

#     vpc_id: str | None = None

#     subnet_id: str | None = None

#     private_ip: str | None = None

#     public_ip: str | None = None

#     iam_instance_profile: str | None = None

#     security_group_ids: list[str] = Field(
#         default_factory=list
#     )

#     volume_ids: list[str] = Field(
#         default_factory=list
#     )

#     tags: dict[str, str] = Field(
#         default_factory=dict
#     )


# class AWSSubnet(BaseModel):
#     subnet_id: str

#     vpc_id: str | None = None

#     region: str

#     availability_zone: str | None = None

#     cidr_block: str | None = None

#     map_public_ip_on_launch: bool | None = None


# class AWSRoute(BaseModel):
#     destination: str | None = None

#     target: str | None = None

#     state: str | None = None


# class AWSRouteTable(BaseModel):
#     route_table_id: str

#     vpc_id: str | None = None

#     region: str

#     routes: list[AWSRoute] = Field(
#         default_factory=list
#     )


# class AWSEC2DeepScanResult(BaseModel):
#     instances: list[
#         AWSEC2Instance
#     ] = Field(default_factory=list)

#     security_groups: list[
#         AWSSecurityGroup
#     ] = Field(default_factory=list)

#     volumes: list[
#         AWSEBSVolume
#     ] = Field(default_factory=list)

#     subnets: list[
#         AWSSubnet
#     ] = Field(default_factory=list)

#     route_tables: list[
#         AWSRouteTable
#     ] = Field(default_factory=list)

#     warnings: list[str] = Field(
#         default_factory=list
#     )
    
    
# class AWSScanSummary(BaseModel):
#     account_id: str

#     enabled_regions: int = 0
#     disabled_regions: int = 0

#     availability_zones: int = 0

#     used_regions: int = 0

#     detected_services: int = 0

#     discovered_resources: int = 0

#     billing_available: bool = False
#     primary_paid_services: int = 0
#     supporting_services: int = 0
#     paid_regions: int = 0

#     # deep_scanned_services: int = 0


# class AWSScanResult(BaseModel):
#     scan_id: str

#     status: str

#     started_at: datetime
#     completed_at: datetime | None = None

#     account: AWSIdentity | None = None

#     regions: AWSRegionDiscoveryResult | None = None

#     zones: AWSZoneDiscoveryResult | None = None

#     resources: AWSResourceDiscoveryResult | None = None

#     billing: AWSBillingDiscoveryResult | None = None

#     classification: AWSInfrastructureClassificationResult | None = None

#     # deep_scan: dict[str, Any] = Field(
#     #     default_factory=dict
#     # )

#     summary: AWSScanSummary | None = None

#     timings: dict[str, int] = Field(
#         default_factory=dict
#     )

#     warnings: list[str] = Field(
#         default_factory=list
#     )
    
# class AWSS3PublicAccessBlock(BaseModel):
#     block_public_acls: bool | None = None
#     ignore_public_acls: bool | None = None
#     block_public_policy: bool | None = None
#     restrict_public_buckets: bool | None = None


# class AWSS3Encryption(BaseModel):
#     enabled: bool = False
#     algorithm: str | None = None
#     kms_key_id: str | None = None
#     bucket_key_enabled: bool | None = None


# class AWSS3Bucket(BaseModel):
#     name: str

#     region: str | None = None

#     creation_date: str | None = None

#     versioning_status: str | None = None

#     mfa_delete: str | None = None

#     public_access_block: (
#         AWSS3PublicAccessBlock | None
#     ) = None

#     encryption: (
#         AWSS3Encryption | None
#     ) = None

#     policy_public: bool | None = None

#     logging_enabled: bool | None = None

#     logging_target_bucket: str | None = None

#     acl_grants: list[dict] = Field(
#         default_factory=list
#     )

#     warnings: list[str] = Field(
#         default_factory=list
#     )


# class AWSS3DeepScanResult(BaseModel):
#     buckets: list[AWSS3Bucket] = Field(
#         default_factory=list
#     )

#     warnings: list[str] = Field(
#         default_factory=list
#     )
    
    
# class AWSDeepScanResult(BaseModel):
#     services: dict[str, Any] = Field(
#         default_factory=dict
#     )

#     warnings: list[str] = Field(
#         default_factory=list
#     )
    
# class AWSRDSInstance(BaseModel):
#     db_instance_identifier: str

#     arn: str | None = None

#     engine: str | None = None
#     engine_version: str | None = None

#     db_instance_class: str | None = None

#     status: str | None = None

#     region: str
#     availability_zone: str | None = None

#     endpoint: str | None = None
#     port: int | None = None

#     publicly_accessible: bool | None = None

#     storage_encrypted: bool | None = None
#     kms_key_id: str | None = None

#     multi_az: bool | None = None

#     backup_retention_period: int | None = None

#     deletion_protection: bool | None = None

#     auto_minor_version_upgrade: bool | None = None

#     iam_database_authentication_enabled: bool | None = None

#     performance_insights_enabled: bool | None = None

#     ca_certificate_identifier: str | None = None

#     vpc_id: str | None = None

#     subnet_ids: list[str] = Field(
#         default_factory=list
#     )

#     security_group_ids: list[str] = Field(
#         default_factory=list
#     )

#     db_cluster_identifier: str | None = None

#     tags: dict[str, str] = Field(
#         default_factory=dict
#     )


# class AWSRDSCluster(BaseModel):
#     db_cluster_identifier: str

#     arn: str | None = None

#     engine: str | None = None
#     engine_version: str | None = None

#     status: str | None = None

#     region: str

#     endpoint: str | None = None
#     reader_endpoint: str | None = None
#     port: int | None = None

#     storage_encrypted: bool | None = None
#     kms_key_id: str | None = None

#     backup_retention_period: int | None = None

#     deletion_protection: bool | None = None

#     iam_database_authentication_enabled: bool | None = None

#     availability_zones: list[str] = Field(
#         default_factory=list
#     )

#     security_group_ids: list[str] = Field(
#         default_factory=list
#     )


# class AWSRDSDeepScanResult(BaseModel):
#     instances: list[AWSRDSInstance] = Field(
#         default_factory=list
#     )

#     clusters: list[AWSRDSCluster] = Field(
#         default_factory=list
#     )

#     warnings: list[str] = Field(
#         default_factory=list
#     )


# class AWSIAMAccessKey(BaseModel):
#     access_key_id: str

#     status: str | None = None

#     create_date: str | None = None


# class AWSIAMMFADevice(BaseModel):
#     serial_number: str

#     enable_date: str | None = None


# class AWSIAMUser(BaseModel):
#     user_name: str

#     user_id: str | None = None

#     arn: str | None = None

#     path: str | None = None

#     create_date: str | None = None

#     password_last_used: str | None = None

#     mfa_devices: list[
#         AWSIAMMFADevice
#     ] = Field(default_factory=list)

#     access_keys: list[
#         AWSIAMAccessKey
#     ] = Field(default_factory=list)

#     groups: list[str] = Field(
#         default_factory=list
#     )

#     attached_policies: list[str] = Field(
#         default_factory=list
#     )

#     inline_policy_names: list[str] = Field(
#         default_factory=list
#     )


# class AWSIAMRole(BaseModel):
#     role_name: str

#     role_id: str | None = None

#     arn: str | None = None

#     path: str | None = None

#     create_date: str | None = None

#     max_session_duration: int | None = None

#     attached_policies: list[str] = Field(
#         default_factory=list
#     )

#     inline_policy_names: list[str] = Field(
#         default_factory=list
#     )


# class AWSIAMPasswordPolicy(BaseModel):
#     minimum_password_length: int | None = None

#     require_symbols: bool | None = None

#     require_numbers: bool | None = None

#     require_uppercase_characters: bool | None = None

#     require_lowercase_characters: bool | None = None

#     allow_users_to_change_password: bool | None = None

#     expire_passwords: bool | None = None

#     max_password_age: int | None = None

#     password_reuse_prevention: int | None = None

#     hard_expiry: bool | None = None


# class AWSIAMDeepScanResult(BaseModel):
#     account_summary: dict = Field(
#         default_factory=dict
#     )

#     password_policy: (
#         AWSIAMPasswordPolicy | None
#     ) = None

#     users: list[AWSIAMUser] = Field(
#         default_factory=list
#     )

#     roles: list[AWSIAMRole] = Field(
#         default_factory=list
#     )

#     warnings: list[str] = Field(
#         default_factory=list
#     )




from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel,Field


class AWSIdentity(BaseModel):
    account_id: str
    arn: str
    user_id: str

    provider: str = "AWS"
    connection_status: str = "VERIFIED"


class AWSRegion(BaseModel):
    region_name: str
    endpoint: str | None = None
    opt_in_status: str | None = None
    enabled: bool


class AWSRegionDiscoveryResult(BaseModel):
    total_regions: int
    enabled_regions: int
    disabled_regions: int
    regions: list[AWSRegion]


class AWSAvailabilityZone(BaseModel):
    zone_name: str
    zone_id: str | None = None
    region_name: str

    state: str | None = None
    zone_type: str | None = None
    opt_in_status: str | None = None


class AWSZoneDiscoveryResult(BaseModel):
    total_zones: int
    zones: list[AWSAvailabilityZone]

class AWSResource(BaseModel):
    arn : str | None = None
    
    resource_id: str | None = None
    resource_type: str | None = None
    
    service: str | None = None
    
    region: str | None = None
    
    owning_account_id: str | None = None
    
    properties: list[dict[str, Any]] = Field(
        default_factory=list
    )
    
class AWSDetectedService(BaseModel):
    service : str
    resource_count: int
    regions: list[str] = Field(
        default_factory=list
    )
    
class AWSResourceDiscoveryResult(BaseModel):
    total_resources: int
    used_regions: list[str]
    detected_services: list[AWSDetectedService]
    resources: list[AWSResource]
    warnings : list[str] = Field(
        default_factory=list
    )


class AWSBillingServiceCost(BaseModel):
    billing_service: str
    amount: float
    unit: str = "USD"


class AWSBillingComponent(BaseModel):
    billing_service: str
    usage_type: str
    amount: float
    unit: str = "USD"


class AWSBillingRegionCost(BaseModel):
    region: str
    amount: float
    unit: str = "USD"


class AWSBillingDiscoveryResult(BaseModel):
    available: bool = False
    period_start: str
    period_end_exclusive: str
    metric: str = "UnblendedCost"
    currency: str = "USD"
    total_cost: float = 0.0
    service_costs: list[AWSBillingServiceCost] = Field(default_factory=list)
    components: list[AWSBillingComponent] = Field(default_factory=list)
    region_costs: list[AWSBillingRegionCost] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AWSResourceRelationship(BaseModel):
    source_arn: str | None = None
    source_resource_id: str | None = None
    source_service: str | None = None
    target_arn: str | None = None
    target_resource_id: str | None = None
    target_service: str | None = None
    evidence: str


class AWSClassifiedService(BaseModel):
    key: str
    category: str
    paid: bool
    financial_status: str = "NO_BILLING_RECORD"
    billing_amount: float = 0.0
    currency: str = "USD"
    billing_services: list[str] = Field(default_factory=list)
    billing_components: list[AWSBillingComponent] = Field(default_factory=list)
    discovered_service: str | None = None
    resource_count: int = 0
    regions: list[str] = Field(default_factory=list)
    related_primary_services: list[str] = Field(default_factory=list)
    billing_match_method: str | None = None
    billing_match_confidence: float | None = None


class AWSClassifiedRegion(BaseModel):
    region: str
    category: str
    billing_amount: float = 0.0
    currency: str = "USD"
    resource_count: int = 0
    enabled: bool = False


class AWSInfrastructureClassificationResult(BaseModel):
    billing_available: bool = False
    primary_paid_services: list[AWSClassifiedService] = Field(default_factory=list)
    zero_cost_services: list[AWSClassifiedService] = Field(default_factory=list)
    supporting_services: list[AWSClassifiedService] = Field(default_factory=list)
    discovered_unbilled_services: list[AWSClassifiedService] = Field(default_factory=list)
    billing_only_services: list[AWSClassifiedService] = Field(default_factory=list)
    non_positive_billing_services: list[AWSClassifiedService] = Field(default_factory=list)
    paid_regions: list[AWSClassifiedRegion] = Field(default_factory=list)
    used_unbilled_regions: list[AWSClassifiedRegion] = Field(default_factory=list)
    enabled_unused_regions: list[AWSClassifiedRegion] = Field(default_factory=list)
    billed_only_regions: list[AWSClassifiedRegion] = Field(default_factory=list)
    relationships: list[AWSResourceRelationship] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AWSSecurityGroupRule(BaseModel):
    protocol : str | None = None
    from_port: int | None = None
    to_port: int | None = None
    
    ipv4_ranges: list[str] = Field(
        default_factory=list
    )
    
    ipv6_ranges: list[str] = Field(
        default_factory=list
    )
    

class AWSSecurityGroup(BaseModel):
    group_id: str

    group_name: str | None = None

    description: str | None = None

    vpc_id: str | None = None
    
    region: str | None = None

    ingress_rules: list[
        AWSSecurityGroupRule
    ] = Field(default_factory=list)

    egress_rules: list[
        AWSSecurityGroupRule
    ] = Field(default_factory=list)


class AWSEBSVolume(BaseModel):
    volume_id: str
    
    region: str | None = None

    size_gb: int | None = None

    volume_type: str | None = None

    encrypted: bool | None = None

    kms_key_id: str | None = None

    state: str | None = None

    availability_zone: str | None = None


class AWSEC2Instance(BaseModel):
    instance_id: str

    name: str | None = None

    instance_type: str | None = None

    state: str | None = None

    region: str

    availability_zone: str | None = None

    vpc_id: str | None = None

    subnet_id: str | None = None

    private_ip: str | None = None

    public_ip: str | None = None

    iam_instance_profile: str | None = None

    security_group_ids: list[str] = Field(
        default_factory=list
    )

    volume_ids: list[str] = Field(
        default_factory=list
    )

    tags: dict[str, str] = Field(
        default_factory=dict
    )


class AWSSubnet(BaseModel):
    subnet_id: str

    vpc_id: str | None = None

    region: str

    availability_zone: str | None = None

    cidr_block: str | None = None

    map_public_ip_on_launch: bool | None = None


class AWSRoute(BaseModel):
    destination: str | None = None

    target: str | None = None

    state: str | None = None


class AWSRouteTable(BaseModel):
    route_table_id: str

    vpc_id: str | None = None

    region: str

    routes: list[AWSRoute] = Field(
        default_factory=list
    )


class AWSEC2DeepScanResult(BaseModel):
    instances: list[
        AWSEC2Instance
    ] = Field(default_factory=list)

    security_groups: list[
        AWSSecurityGroup
    ] = Field(default_factory=list)

    volumes: list[
        AWSEBSVolume
    ] = Field(default_factory=list)

    subnets: list[
        AWSSubnet
    ] = Field(default_factory=list)

    route_tables: list[
        AWSRouteTable
    ] = Field(default_factory=list)

    warnings: list[str] = Field(
        default_factory=list
    )
    
    
class AWSScanSummary(BaseModel):
    account_id: str

    enabled_regions: int = 0
    disabled_regions: int = 0

    availability_zones: int = 0

    used_regions: int = 0

    detected_services: int = 0

    discovered_resources: int = 0

    billing_available: bool = False
    primary_paid_services: int = 0
    zero_cost_services: int = 0
    supporting_services: int = 0
    paid_regions: int = 0

    # deep_scanned_services: int = 0


class AWSScanResult(BaseModel):
    scan_id: str

    status: str

    started_at: datetime
    completed_at: datetime | None = None

    account: AWSIdentity | None = None

    regions: AWSRegionDiscoveryResult | None = None

    zones: AWSZoneDiscoveryResult | None = None

    resources: AWSResourceDiscoveryResult | None = None

    billing: AWSBillingDiscoveryResult | None = None

    classification: AWSInfrastructureClassificationResult | None = None

    # deep_scan: dict[str, Any] = Field(
    #     default_factory=dict
    # )

    summary: AWSScanSummary | None = None

    timings: dict[str, int] = Field(
        default_factory=dict
    )

    warnings: list[str] = Field(
        default_factory=list
    )
    
class AWSS3PublicAccessBlock(BaseModel):
    block_public_acls: bool | None = None
    ignore_public_acls: bool | None = None
    block_public_policy: bool | None = None
    restrict_public_buckets: bool | None = None


class AWSS3Encryption(BaseModel):
    enabled: bool = False
    algorithm: str | None = None
    kms_key_id: str | None = None
    bucket_key_enabled: bool | None = None


class AWSS3Bucket(BaseModel):
    name: str

    region: str | None = None

    creation_date: str | None = None

    versioning_status: str | None = None

    mfa_delete: str | None = None

    public_access_block: (
        AWSS3PublicAccessBlock | None
    ) = None

    encryption: (
        AWSS3Encryption | None
    ) = None

    policy_public: bool | None = None

    logging_enabled: bool | None = None

    logging_target_bucket: str | None = None

    acl_grants: list[dict] = Field(
        default_factory=list
    )

    warnings: list[str] = Field(
        default_factory=list
    )


class AWSS3DeepScanResult(BaseModel):
    buckets: list[AWSS3Bucket] = Field(
        default_factory=list
    )

    warnings: list[str] = Field(
        default_factory=list
    )
    
    
class AWSDeepScanResult(BaseModel):
    services: dict[str, Any] = Field(
        default_factory=dict
    )

    warnings: list[str] = Field(
        default_factory=list
    )
    
class AWSRDSInstance(BaseModel):
    db_instance_identifier: str

    arn: str | None = None

    engine: str | None = None
    engine_version: str | None = None

    db_instance_class: str | None = None

    status: str | None = None

    region: str
    availability_zone: str | None = None

    endpoint: str | None = None
    port: int | None = None

    publicly_accessible: bool | None = None

    storage_encrypted: bool | None = None
    kms_key_id: str | None = None

    multi_az: bool | None = None

    backup_retention_period: int | None = None

    deletion_protection: bool | None = None

    auto_minor_version_upgrade: bool | None = None

    iam_database_authentication_enabled: bool | None = None

    performance_insights_enabled: bool | None = None

    ca_certificate_identifier: str | None = None

    vpc_id: str | None = None

    subnet_ids: list[str] = Field(
        default_factory=list
    )

    security_group_ids: list[str] = Field(
        default_factory=list
    )

    db_cluster_identifier: str | None = None

    tags: dict[str, str] = Field(
        default_factory=dict
    )


class AWSRDSCluster(BaseModel):
    db_cluster_identifier: str

    arn: str | None = None

    engine: str | None = None
    engine_version: str | None = None

    status: str | None = None

    region: str

    endpoint: str | None = None
    reader_endpoint: str | None = None
    port: int | None = None

    storage_encrypted: bool | None = None
    kms_key_id: str | None = None

    backup_retention_period: int | None = None

    deletion_protection: bool | None = None

    iam_database_authentication_enabled: bool | None = None

    availability_zones: list[str] = Field(
        default_factory=list
    )

    security_group_ids: list[str] = Field(
        default_factory=list
    )


class AWSRDSDeepScanResult(BaseModel):
    instances: list[AWSRDSInstance] = Field(
        default_factory=list
    )

    clusters: list[AWSRDSCluster] = Field(
        default_factory=list
    )

    warnings: list[str] = Field(
        default_factory=list
    )


class AWSIAMAccessKey(BaseModel):
    access_key_id: str

    status: str | None = None

    create_date: str | None = None


class AWSIAMMFADevice(BaseModel):
    serial_number: str

    enable_date: str | None = None


class AWSIAMUser(BaseModel):
    user_name: str

    user_id: str | None = None

    arn: str | None = None

    path: str | None = None

    create_date: str | None = None

    password_last_used: str | None = None

    mfa_devices: list[
        AWSIAMMFADevice
    ] = Field(default_factory=list)

    access_keys: list[
        AWSIAMAccessKey
    ] = Field(default_factory=list)

    groups: list[str] = Field(
        default_factory=list
    )

    attached_policies: list[str] = Field(
        default_factory=list
    )

    inline_policy_names: list[str] = Field(
        default_factory=list
    )


class AWSIAMRole(BaseModel):
    role_name: str

    role_id: str | None = None

    arn: str | None = None

    path: str | None = None

    create_date: str | None = None

    max_session_duration: int | None = None

    attached_policies: list[str] = Field(
        default_factory=list
    )

    inline_policy_names: list[str] = Field(
        default_factory=list
    )


class AWSIAMPasswordPolicy(BaseModel):
    minimum_password_length: int | None = None

    require_symbols: bool | None = None

    require_numbers: bool | None = None

    require_uppercase_characters: bool | None = None

    require_lowercase_characters: bool | None = None

    allow_users_to_change_password: bool | None = None

    expire_passwords: bool | None = None

    max_password_age: int | None = None

    password_reuse_prevention: int | None = None

    hard_expiry: bool | None = None


class AWSIAMDeepScanResult(BaseModel):
    account_summary: dict = Field(
        default_factory=dict
    )

    password_policy: (
        AWSIAMPasswordPolicy | None
    ) = None

    users: list[AWSIAMUser] = Field(
        default_factory=list
    )

    roles: list[AWSIAMRole] = Field(
        default_factory=list
    )

    warnings: list[str] = Field(
        default_factory=list
    )





