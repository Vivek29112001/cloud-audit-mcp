from __future__ import annotations

from typing import Any

from app.providers.aws.collectors.base import AWSDeepCollector
from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.mcp_client import AWSMCPClient
from app.providers.aws.models import AWSEC2DeepScanResult
from app.providers.aws.result_parser import (
    extract_mcp_result,
    find_dict_with_keys,
)


class EC2DeepCollector(AWSDeepCollector):
    @property
    def service_name(self) -> str:
        return "ec2"

    async def collect(
        self,
        credentials: AWSCredentials,
        regions: list[str],
    ) -> dict[str, Any]:
        client = AWSMCPClient(credentials)

        all_data: dict[str, Any] = {
            "instances": [],
            "security_groups": [],
            "volumes": [],
            "subnets": [],
            "route_tables": [],
            "warnings": [],
        }

        for region in sorted(set(regions)):
            if not region or region == "global":
                continue

            try:
                result = await self._collect_region(
                    client=client,
                    region=region,
                )

                for key in (
                    "instances",
                    "security_groups",
                    "volumes",
                    "subnets",
                    "route_tables",
                ):
                    all_data[key].extend(result.get(key, []))

            except Exception as exc:
                all_data["warnings"].append(
                    f"EC2 deep scan failed for {region}: {exc}"
                )

        # Validate/normalize the complete output with Pydantic.
        validated = AWSEC2DeepScanResult.model_validate(all_data)
        return validated.model_dump()

    async def _collect_region(
        self,
        client: AWSMCPClient,
        region: str,
    ) -> dict[str, Any]:
        script = f"""
region = {region!r}

result = {{
    "instances": [],
    "security_groups": [],
    "volumes": [],
    "subnets": [],
    "route_tables": [],
}}

# ---------------------------------------------------------
# EC2 INSTANCES
# ---------------------------------------------------------
next_token = None

while True:
    params = {{"MaxResults": 1000}}
    if next_token:
        params["NextToken"] = next_token

    response = await call_boto3(
        service_name="ec2",
        operation_name="DescribeInstances",
        region_name=region,
        params=params
    )

    for reservation in response.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            tags = {{
                tag.get("Key"): tag.get("Value")
                for tag in instance.get("Tags", [])
                if tag.get("Key")
            }}

            security_group_ids = [
                sg.get("GroupId")
                for sg in instance.get("SecurityGroups", [])
                if sg.get("GroupId")
            ]

            volume_ids = []
            for mapping in instance.get("BlockDeviceMappings", []):
                ebs = mapping.get("Ebs", {{}})
                volume_id = ebs.get("VolumeId")
                if volume_id:
                    volume_ids.append(volume_id)

            result["instances"].append({{
                "instance_id": instance.get("InstanceId"),
                "name": tags.get("Name"),
                "instance_type": instance.get("InstanceType"),
                "state": instance.get("State", {{}}).get("Name"),
                "region": region,
                "availability_zone": instance.get("Placement", {{}}).get(
                    "AvailabilityZone"
                ),
                "vpc_id": instance.get("VpcId"),
                "subnet_id": instance.get("SubnetId"),
                "private_ip": instance.get("PrivateIpAddress"),
                "public_ip": instance.get("PublicIpAddress"),
                "iam_instance_profile": instance.get(
                    "IamInstanceProfile", {{}}
                ).get("Arn"),
                "security_group_ids": security_group_ids,
                "volume_ids": volume_ids,
                "tags": tags,
            }})

    next_token = response.get("NextToken")
    if not next_token:
        break

# ---------------------------------------------------------
# SECURITY GROUPS
# ---------------------------------------------------------
next_token = None

while True:
    params = {{"MaxResults": 1000}}
    if next_token:
        params["NextToken"] = next_token

    response = await call_boto3(
        service_name="ec2",
        operation_name="DescribeSecurityGroups",
        region_name=region,
        params=params
    )

    for sg in response.get("SecurityGroups", []):
        ingress_rules = []

        for rule in sg.get("IpPermissions", []):
            ingress_rules.append({{
                "protocol": rule.get("IpProtocol"),
                "from_port": rule.get("FromPort"),
                "to_port": rule.get("ToPort"),
                "ipv4_ranges": [
                    item.get("CidrIp")
                    for item in rule.get("IpRanges", [])
                    if item.get("CidrIp")
                ],
                "ipv6_ranges": [
                    item.get("CidrIpv6")
                    for item in rule.get("Ipv6Ranges", [])
                    if item.get("CidrIpv6")
                ],
            }})

        egress_rules = []

        for rule in sg.get("IpPermissionsEgress", []):
            egress_rules.append({{
                "protocol": rule.get("IpProtocol"),
                "from_port": rule.get("FromPort"),
                "to_port": rule.get("ToPort"),
                "ipv4_ranges": [
                    item.get("CidrIp")
                    for item in rule.get("IpRanges", [])
                    if item.get("CidrIp")
                ],
                "ipv6_ranges": [
                    item.get("CidrIpv6")
                    for item in rule.get("Ipv6Ranges", [])
                    if item.get("CidrIpv6")
                ],
            }})

        result["security_groups"].append({{
            "group_id": sg.get("GroupId"),
            "group_name": sg.get("GroupName"),
            "description": sg.get("Description"),
            "vpc_id": sg.get("VpcId"),
            "region": region,
            "ingress_rules": ingress_rules,
            "egress_rules": egress_rules,
        }})

    next_token = response.get("NextToken")
    if not next_token:
        break

# ---------------------------------------------------------
# EBS VOLUMES
# ---------------------------------------------------------
next_token = None

while True:
    params = {{"MaxResults": 500}}
    if next_token:
        params["NextToken"] = next_token

    response = await call_boto3(
        service_name="ec2",
        operation_name="DescribeVolumes",
        region_name=region,
        params=params
    )

    for volume in response.get("Volumes", []):
        result["volumes"].append({{
            "volume_id": volume.get("VolumeId"),
            "region": region,
            "size_gb": volume.get("Size"),
            "volume_type": volume.get("VolumeType"),
            "encrypted": volume.get("Encrypted"),
            "kms_key_id": volume.get("KmsKeyId"),
            "state": volume.get("State"),
            "availability_zone": volume.get("AvailabilityZone"),
        }})

    next_token = response.get("NextToken")
    if not next_token:
        break

# ---------------------------------------------------------
# SUBNETS
# ---------------------------------------------------------
next_token = None

while True:
    params = {{"MaxResults": 1000}}
    if next_token:
        params["NextToken"] = next_token

    response = await call_boto3(
        service_name="ec2",
        operation_name="DescribeSubnets",
        region_name=region,
        params=params
    )

    for subnet in response.get("Subnets", []):
        result["subnets"].append({{
            "subnet_id": subnet.get("SubnetId"),
            "vpc_id": subnet.get("VpcId"),
            "region": region,
            "availability_zone": subnet.get("AvailabilityZone"),
            "cidr_block": subnet.get("CidrBlock"),
            "map_public_ip_on_launch": subnet.get(
                "MapPublicIpOnLaunch"
            ),
        }})

    next_token = response.get("NextToken")
    if not next_token:
        break

# ---------------------------------------------------------
# ROUTE TABLES
# ---------------------------------------------------------
next_token = None

while True:
    params = {{"MaxResults": 100}}
    if next_token:
        params["NextToken"] = next_token

    response = await call_boto3(
        service_name="ec2",
        operation_name="DescribeRouteTables",
        region_name=region,
        params=params
    )

    for table in response.get("RouteTables", []):
        routes = []

        for route in table.get("Routes", []):
            destination = (
                route.get("DestinationCidrBlock")
                or route.get("DestinationIpv6CidrBlock")
                or route.get("DestinationPrefixListId")
            )

            target = (
                route.get("GatewayId")
                or route.get("NatGatewayId")
                or route.get("TransitGatewayId")
                or route.get("NetworkInterfaceId")
                or route.get("InstanceId")
                or route.get("VpcPeeringConnectionId")
            )

            routes.append({{
                "destination": destination,
                "target": target,
                "state": route.get("State"),
            }})

        result["route_tables"].append({{
            "route_table_id": table.get("RouteTableId"),
            "vpc_id": table.get("VpcId"),
            "region": region,
            "routes": routes,
        }})

    next_token = response.get("NextToken")
    if not next_token:
        break

result
"""

        response = await client.execute_aws_script(script)
        parsed = extract_mcp_result(response)

        expected = {
            "instances",
            "security_groups",
            "volumes",
            "subnets",
            "route_tables",
        }

        found = find_dict_with_keys(parsed, expected)
        if not found:
            raise RuntimeError(
                f"EC2 MCP response for {region} did not contain "
                "the expected deep-scan structure."
            )

        return found
