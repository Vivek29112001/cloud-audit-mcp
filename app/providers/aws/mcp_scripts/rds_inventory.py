def build_rds_inventory_script(
    region: str,
) -> str:

    return f"""
region = {region!r}

result = {{
    "instances": [],
    "clusters": [],
    "warnings": []
}}

#
# ---------------------------------------
# RDS INSTANCES
# ---------------------------------------
#

marker = None

while True:

    params = {{
        "MaxRecords": 100
    }}

    if marker:
        params["Marker"] = marker

    response = await call_boto3(
        service_name="rds",
        operation_name="DescribeDBInstances",
        region_name=region,
        params=params
    )

    for db in response.get(
        "DBInstances",
        []
    ):

        subnet_group = (
            db.get("DBSubnetGroup")
            or {{}}
        )

        subnet_ids = []

        for subnet in subnet_group.get(
            "Subnets",
            []
        ):
            subnet_id = subnet.get(
                "SubnetIdentifier"
            )

            if subnet_id:
                subnet_ids.append(
                    subnet_id
                )

        security_group_ids = [
            item.get(
                "VpcSecurityGroupId"
            )
            for item in db.get(
                "VpcSecurityGroups",
                []
            )
            if item.get(
                "VpcSecurityGroupId"
            )
        ]

        endpoint_data = (
            db.get("Endpoint")
            or {{}}
        )

        tags = {{}}

        arn = db.get(
            "DBInstanceArn"
        )

        if arn:

            try:
                tag_response = await call_boto3(
                    service_name="rds",
                    operation_name=(
                        "ListTagsForResource"
                    ),
                    region_name=region,
                    params={{
                        "ResourceName": arn
                    }}
                )

                for tag in tag_response.get(
                    "TagList",
                    []
                ):
                    key = tag.get("Key")

                    if key:
                        tags[key] = tag.get(
                            "Value"
                        )

            except Exception as exc:

                result[
                    "warnings"
                ].append(
                    "Unable to retrieve tags "
                    "for RDS instance "
                    + str(
                        db.get(
                            "DBInstanceIdentifier"
                        )
                    )
                    + ": "
                    + str(exc)
                )

        result[
            "instances"
        ].append({{
            "db_instance_identifier":
                db.get(
                    "DBInstanceIdentifier"
                ),

            "arn":
                arn,

            "engine":
                db.get("Engine"),

            "engine_version":
                db.get(
                    "EngineVersion"
                ),

            "db_instance_class":
                db.get(
                    "DBInstanceClass"
                ),

            "status":
                db.get(
                    "DBInstanceStatus"
                ),

            "region":
                region,

            "availability_zone":
                db.get(
                    "AvailabilityZone"
                ),

            "endpoint":
                endpoint_data.get(
                    "Address"
                ),

            "port":
                endpoint_data.get(
                    "Port"
                ),

            "publicly_accessible":
                db.get(
                    "PubliclyAccessible"
                ),

            "storage_encrypted":
                db.get(
                    "StorageEncrypted"
                ),

            "kms_key_id":
                db.get(
                    "KmsKeyId"
                ),

            "multi_az":
                db.get(
                    "MultiAZ"
                ),

            "backup_retention_period":
                db.get(
                    "BackupRetentionPeriod"
                ),

            "deletion_protection":
                db.get(
                    "DeletionProtection"
                ),

            "auto_minor_version_upgrade":
                db.get(
                    "AutoMinorVersionUpgrade"
                ),

            "iam_database_authentication_enabled":
                db.get(
                    "IAMDatabaseAuthenticationEnabled"
                ),

            "performance_insights_enabled":
                db.get(
                    "PerformanceInsightsEnabled"
                ),

            "ca_certificate_identifier":
                db.get(
                    "CACertificateIdentifier"
                ),

            "vpc_id":
                subnet_group.get(
                    "VpcId"
                ),

            "subnet_ids":
                subnet_ids,

            "security_group_ids":
                security_group_ids,

            "db_cluster_identifier":
                db.get(
                    "DBClusterIdentifier"
                ),

            "tags":
                tags
        }})

    marker = response.get(
        "Marker"
    )

    if not marker:
        break


#
# ---------------------------------------
# RDS / AURORA CLUSTERS
# ---------------------------------------
#

marker = None

while True:

    params = {{
        "MaxRecords": 100
    }}

    if marker:
        params["Marker"] = marker

    response = await call_boto3(
        service_name="rds",
        operation_name="DescribeDBClusters",
        region_name=region,
        params=params
    )

    for cluster in response.get(
        "DBClusters",
        []
    ):

        security_group_ids = [
            item.get(
                "VpcSecurityGroupId"
            )
            for item in cluster.get(
                "VpcSecurityGroups",
                []
            )
            if item.get(
                "VpcSecurityGroupId"
            )
        ]

        result[
            "clusters"
        ].append({{
            "db_cluster_identifier":
                cluster.get(
                    "DBClusterIdentifier"
                ),

            "arn":
                cluster.get(
                    "DBClusterArn"
                ),

            "engine":
                cluster.get(
                    "Engine"
                ),

            "engine_version":
                cluster.get(
                    "EngineVersion"
                ),

            "status":
                cluster.get(
                    "Status"
                ),

            "region":
                region,

            "endpoint":
                cluster.get(
                    "Endpoint"
                ),

            "reader_endpoint":
                cluster.get(
                    "ReaderEndpoint"
                ),

            "port":
                cluster.get(
                    "Port"
                ),

            "storage_encrypted":
                cluster.get(
                    "StorageEncrypted"
                ),

            "kms_key_id":
                cluster.get(
                    "KmsKeyId"
                ),

            "backup_retention_period":
                cluster.get(
                    "BackupRetentionPeriod"
                ),

            "deletion_protection":
                cluster.get(
                    "DeletionProtection"
                ),

            "iam_database_authentication_enabled":
                cluster.get(
                    "IAMDatabaseAuthenticationEnabled"
                ),

            "availability_zones":
                cluster.get(
                    "AvailabilityZones",
                    []
                ),

            "security_group_ids":
                security_group_ids
        }})

    marker = response.get(
        "Marker"
    )

    if not marker:
        break


result
"""