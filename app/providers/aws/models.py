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

    deep_scanned_services: int = 0


class AWSScanResult(BaseModel):
    scan_id: str

    status: str

    started_at: datetime
    completed_at: datetime | None = None

    account: AWSIdentity | None = None

    regions: AWSRegionDiscoveryResult | None = None

    zones: AWSZoneDiscoveryResult | None = None

    resources: AWSResourceDiscoveryResult | None = None

    deep_scan: dict[str, Any] = Field(
        default_factory=dict
    )

    summary: AWSScanSummary | None = None

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
    

