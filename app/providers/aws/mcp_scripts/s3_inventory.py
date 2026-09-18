def build_s3_inventory_script() -> str:
    return r'''
result = {
    "buckets": [],
    "warnings": []
}

#
# -------------------------------------------------
# LIST ALL S3 BUCKETS
# -------------------------------------------------
#

bucket_response = await call_boto3(
    service_name="s3",
    operation_name="ListBuckets",
    region_name="us-east-1",
    params={}
)

for bucket in bucket_response.get("Buckets", []):

    bucket_name = bucket.get("Name")

    bucket_result = {
        "name": bucket_name,
        "region": None,
        "creation_date": (
            str(bucket.get("CreationDate"))
            if bucket.get("CreationDate")
            else None
        ),
        "versioning_status": None,
        "mfa_delete": None,
        "public_access_block": None,
        "encryption": {
            "enabled": False,
            "algorithm": None,
            "kms_key_id": None,
            "bucket_key_enabled": None
        },
        "policy_public": None,
        "logging_enabled": None,
        "logging_target_bucket": None,
        "acl_grants": [],
        "warnings": []
    }

    #
    # ---------------------------------------------
    # BUCKET REGION
    # ---------------------------------------------
    #

    try:
        location = await call_boto3(
            service_name="s3",
            operation_name="GetBucketLocation",
            region_name="us-east-1",
            params={
                "Bucket": bucket_name
            }
        )

        location_constraint = location.get(
            "LocationConstraint"
        )

        # AWS historical behavior:
        # null means us-east-1.
        bucket_region = (
            location_constraint
            or "us-east-1"
        )

        # Legacy EU value maps to eu-west-1.
        if bucket_region == "EU":
            bucket_region = "eu-west-1"

        bucket_result["region"] = bucket_region

    except Exception as exc:
        bucket_result["warnings"].append(
            "GetBucketLocation failed: "
            + str(exc)
        )

        bucket_region = "us-east-1"

    #
    # ---------------------------------------------
    # VERSIONING
    # ---------------------------------------------
    #

    try:
        versioning = await call_boto3(
            service_name="s3",
            operation_name="GetBucketVersioning",
            region_name=bucket_region,
            params={
                "Bucket": bucket_name
            }
        )

        bucket_result[
            "versioning_status"
        ] = versioning.get("Status")

        bucket_result[
            "mfa_delete"
        ] = versioning.get("MFADelete")

    except Exception as exc:
        bucket_result["warnings"].append(
            "GetBucketVersioning failed: "
            + str(exc)
        )

    #
    # ---------------------------------------------
    # PUBLIC ACCESS BLOCK
    # ---------------------------------------------
    #

    try:
        public_access = await call_boto3(
            service_name="s3",
            operation_name="GetPublicAccessBlock",
            region_name=bucket_region,
            params={
                "Bucket": bucket_name
            }
        )

        config = public_access.get(
            "PublicAccessBlockConfiguration",
            {}
        )

        bucket_result[
            "public_access_block"
        ] = {
            "block_public_acls":
                config.get(
                    "BlockPublicAcls"
                ),

            "ignore_public_acls":
                config.get(
                    "IgnorePublicAcls"
                ),

            "block_public_policy":
                config.get(
                    "BlockPublicPolicy"
                ),

            "restrict_public_buckets":
                config.get(
                    "RestrictPublicBuckets"
                )
        }

    except Exception as exc:
        bucket_result["warnings"].append(
            "GetPublicAccessBlock failed: "
            + str(exc)
        )

    #
    # ---------------------------------------------
    # BUCKET POLICY STATUS
    # ---------------------------------------------
    #

    try:
        policy_status = await call_boto3(
            service_name="s3",
            operation_name="GetBucketPolicyStatus",
            region_name=bucket_region,
            params={
                "Bucket": bucket_name
            }
        )

        bucket_result[
            "policy_public"
        ] = (
            policy_status
            .get(
                "PolicyStatus",
                {}
            )
            .get("IsPublic")
        )

    except Exception as exc:
        bucket_result["warnings"].append(
            "GetBucketPolicyStatus failed: "
            + str(exc)
        )

    #
    # ---------------------------------------------
    # BUCKET ENCRYPTION
    # ---------------------------------------------
    #

    try:
        encryption = await call_boto3(
            service_name="s3",
            operation_name="GetBucketEncryption",
            region_name=bucket_region,
            params={
                "Bucket": bucket_name
            }
        )

        rules = (
            encryption
            .get(
                "ServerSideEncryptionConfiguration",
                {}
            )
            .get("Rules", [])
        )

        if rules:

            first_rule = rules[0]

            default_encryption = (
                first_rule.get(
                    "ApplyServerSideEncryptionByDefault",
                    {}
                )
            )

            bucket_result[
                "encryption"
            ] = {
                "enabled": True,

                "algorithm":
                    default_encryption.get(
                        "SSEAlgorithm"
                    ),

                "kms_key_id":
                    default_encryption.get(
                        "KMSMasterKeyID"
                    ),

                "bucket_key_enabled":
                    first_rule.get(
                        "BucketKeyEnabled"
                    )
            }

    except Exception as exc:
        bucket_result["warnings"].append(
            "GetBucketEncryption failed: "
            + str(exc)
        )

    #
    # ---------------------------------------------
    # ACL
    # ---------------------------------------------
    #

    try:
        acl = await call_boto3(
            service_name="s3",
            operation_name="GetBucketAcl",
            region_name=bucket_region,
            params={
                "Bucket": bucket_name
            }
        )

        bucket_result[
            "acl_grants"
        ] = acl.get(
            "Grants",
            []
        )

    except Exception as exc:
        bucket_result["warnings"].append(
            "GetBucketAcl failed: "
            + str(exc)
        )

    #
    # ---------------------------------------------
    # LOGGING
    # ---------------------------------------------
    #

    try:
        logging = await call_boto3(
            service_name="s3",
            operation_name="GetBucketLogging",
            region_name=bucket_region,
            params={
                "Bucket": bucket_name
            }
        )

        logging_config = logging.get(
            "LoggingEnabled"
        )

        bucket_result[
            "logging_enabled"
        ] = logging_config is not None

        if logging_config:
            bucket_result[
                "logging_target_bucket"
            ] = logging_config.get(
                "TargetBucket"
            )

    except Exception as exc:
        bucket_result["warnings"].append(
            "GetBucketLogging failed: "
            + str(exc)
        )

    result["buckets"].append(
        bucket_result
    )

result
'''