from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.providers.aws.mcp_client import AWSMCPClient
from app.providers.aws.result_parser import extract_mcp_result


@dataclass(frozen=True)
class S3SecurityAuditRequest:
    """
    Deterministic audit requirements derived from the user's S3 question.

    This is intentionally NOT an agent. It only chooses which predefined,
    read-only evidence groups are needed for an S3 audit. Bucket names,
    Regions and account data are always discovered dynamically from AWS.
    """

    check_inventory: bool = False
    check_encryption: bool = False
    check_public_access: bool = False
    check_sensitive_indicators: bool = False
    check_versioning: bool = False
    check_logging: bool = False

    @property
    def needs_live_audit(self) -> bool:
        return any(
            (
                self.check_inventory,
                self.check_encryption,
                self.check_public_access,
                self.check_sensitive_indicators,
                self.check_versioning,
                self.check_logging,
            )
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "check_inventory": self.check_inventory,
            "check_encryption": self.check_encryption,
            "check_public_access": self.check_public_access,
            "check_sensitive_indicators": self.check_sensitive_indicators,
            "check_versioning": self.check_versioning,
            "check_logging": self.check_logging,
        }

    @classmethod
    def from_question(
        cls,
        question: str,
        selected_context: dict[str, Any] | None = None,
    ) -> "S3SecurityAuditRequest | None":
        q = " ".join((question or "").lower().split())
        context = selected_context or {}

        context_service = " ".join(
            str(context.get(key) or "")
            for key in ("service", "label", "billing_service")
        ).lower()

        s3_context = (
            "s3" in context_service
            or "simple storage" in context_service
        )
        s3_question = (
            "s3" in q
            or "bucket" in q
            or "buckets" in q
        )

        if not (s3_context or s3_question):
            return None

        check_inventory = any(
            phrase in q
            for phrase in (
                "all s3 buckets",
                "all buckets",
                "list s3 buckets",
                "list buckets",
                "show s3 buckets",
                "show buckets",
                "check all s3 buckets",
                "check all buckets",
                "bucket inventory",
            )
        )

        check_encryption = any(
            token in q
            for token in (
                "encrypt",
                "encryption",
                "kms",
                "sse-kms",
                "sse_s3",
                "sse-s3",
                "server-side encryption",
            )
        )
        check_public_access = any(
            token in q
            for token in (
                "public",
                "anonymous",
                "bucket policy",
                "acl",
                "access block",
                "public access",
                "exposed",
                "exposure",
            )
        )
        check_sensitive = any(
            token in q
            for token in (
                "sensitive",
                "pii",
                "personal data",
                "object name",
                "object names",
                "prefix",
                "prefixes",
                "metadata",
                "confidential",
                "secret data",
            )
        )
        check_versioning = "version" in q
        check_logging = any(
            token in q
            for token in (
                "logging",
                "access log",
                "server access log",
            )
        )

        general_security = any(
            token in q
            for token in (
                "secure",
                "security",
                "misconfiguration",
                "misconfigured",
                "audit",
                "risk",
            )
        )

        # A broad S3 security question should collect the common posture
        # controls rather than returning only the shallow inventory snapshot.
        if general_security and not any(
            (
                check_encryption,
                check_public_access,
                check_sensitive,
                check_versioning,
                check_logging,
            )
        ):
            check_encryption = True
            check_public_access = True
            check_versioning = True
            check_logging = True

        request = cls(
            check_inventory=check_inventory,
            check_encryption=check_encryption,
            check_public_access=check_public_access,
            check_sensitive_indicators=check_sensitive,
            check_versioning=check_versioning,
            check_logging=check_logging,
        )

        return request if request.needs_live_audit else None


class S3SecurityAuditExecutor:
    """
    Execute a bounded, read-only S3 security audit through AWS Managed MCP.

    Important S3 semantics handled here:
      * ListBuckets is executed ONCE at account scope.
      * Each bucket Region is resolved with GetBucketLocation.
      * A bucket is never duplicated merely because multiple Regions are enabled.
      * Missing GetBucketEncryption evidence is UNKNOWN, not "encryption disabled".
      * Object sensitivity is heuristic and based only on names/prefixes/metadata;
        object content is never downloaded.
    """

    MAX_OBJECT_KEYS_PER_BUCKET = 100
    MAX_METADATA_OBJECTS_PER_BUCKET = 3
    MAX_MATCHED_OBJECTS_RETURNED = 20

    async def execute(
        self,
        *,
        mcp: AWSMCPClient,
        request: S3SecurityAuditRequest,
    ) -> dict[str, Any]:
        script = self._build_script(request)
        response = await mcp.run_aws_script(script)
        parsed = extract_mcp_result(response)
        result = self._find_result(parsed)

        if not result:
            raise RuntimeError(
                "AWS MCP returned no usable S3 security audit result."
            )

        return result

    @classmethod
    def _build_script(
        cls,
        request: S3SecurityAuditRequest,
    ) -> str:
        config_json = json.dumps(
            {
                **request.as_dict(),
                "max_object_keys_per_bucket": cls.MAX_OBJECT_KEYS_PER_BUCKET,
                "max_metadata_objects_per_bucket": cls.MAX_METADATA_OBJECTS_PER_BUCKET,
                "max_matched_objects_returned": cls.MAX_MATCHED_OBJECTS_RETURNED,
            }
        )

        # This code runs inside the AWS Managed MCP execution environment.
        # Every operation below is a fixed read-only AWS API call.
        return rf'''
config = {config_json}

result = {{
    "audit_type": "S3_SECURITY_AUDIT",
    "scope": "ACCOUNT",
    "requirements": config,
    "bucket_count": 0,
    "affected_bucket_count": 0,
    "buckets": [],
    "warnings": []
}}

sensitive_terms = [
    "password", "passwd", "secret", "credential", "credentials",
    "access_key", "access-key", "private_key", "private-key",
    "token", "api_key", "api-key", "ssn", "aadhaar", "aadhar",
    "pan", "passport", "payroll", "salary", "employee", "customer",
    "patient", "medical", "health", "financial", "bank", "invoice",
    "confidential", "pii", "personal", "backup", "database", "db_dump"
]


def _error_text(exc):
    text = str(exc)
    # Keep bounded evidence and avoid returning excessively large provider errors.
    return text[:500]


def _region_from_location(value):
    if not value:
        return "us-east-1"
    if value == "EU":
        return "eu-west-1"
    return value


def _encryption_posture(encryption_response):
    rules = (
        (encryption_response or {{}})
        .get("ServerSideEncryptionConfiguration", {{}})
        .get("Rules", [])
    )

    if not rules:
        return {{
            "evidence_status": "UNKNOWN",
            "algorithm": None,
            "kms_key_id": None,
            "bucket_key_enabled": None,
            "uses_kms": None,
            "posture": "UNKNOWN"
        }}

    first_rule = rules[0] or {{}}
    default_rule = first_rule.get("ApplyServerSideEncryptionByDefault", {{}}) or {{}}
    algorithm = default_rule.get("SSEAlgorithm")
    kms_key_id = default_rule.get("KMSMasterKeyID")

    if algorithm == "aws:kms":
        posture = "SSE_KMS"
        uses_kms = True
    elif algorithm == "aws:kms:dsse":
        posture = "DSSE_KMS"
        uses_kms = True
    elif algorithm == "AES256":
        posture = "SSE_S3"
        uses_kms = False
    else:
        posture = "OTHER" if algorithm else "UNKNOWN"
        uses_kms = False if algorithm else None

    return {{
        "evidence_status": "AVAILABLE",
        "algorithm": algorithm,
        "kms_key_id": kms_key_id,
        "bucket_key_enabled": first_rule.get("BucketKeyEnabled"),
        "uses_kms": uses_kms,
        "posture": posture
    }}


def _public_access_posture(public_block, policy_public, acl_grants):
    block = public_block or {{}}
    all_blocked = all(
        block.get(key) is True
        for key in (
            "BlockPublicAcls",
            "IgnorePublicAcls",
            "BlockPublicPolicy",
            "RestrictPublicBuckets",
        )
    ) if block else False

    public_acl = False
    for grant in acl_grants or []:
        grantee = grant.get("Grantee", {{}}) or {{}}
        uri = str(grantee.get("URI") or "")
        if "AllUsers" in uri or "AuthenticatedUsers" in uri:
            public_acl = True
            break

    if policy_public is True or public_acl:
        return "PUBLIC"
    if all_blocked and policy_public is False:
        return "BLOCKED"
    if all_blocked and policy_public is None:
        return "LIKELY_BLOCKED"
    return "UNKNOWN"


bucket_response = await call_boto3(
    service_name="s3",
    operation_name="ListBuckets",
    region_name="us-east-1",
    params={{}}
)

# Defensive de-duplication even if an upstream response contains duplicate rows.
unique_buckets = {{}}
for bucket in bucket_response.get("Buckets", []) or []:
    name = bucket.get("Name")
    if name and name not in unique_buckets:
        unique_buckets[name] = bucket

result["bucket_count"] = len(unique_buckets)

for bucket_name, bucket in unique_buckets.items():
    bucket_result = {{
        "name": bucket_name,
        "creation_date": str(bucket.get("CreationDate")) if bucket.get("CreationDate") else None,
        "region": None,
        "encryption": None,
        "public_access": None,
        "versioning": None,
        "logging": None,
        "sensitive_data_indicators": {{
            "status": "NOT_CHECKED",
            "level": "UNKNOWN",
            "basis": "Object content was not inspected.",
            "matched_terms": [],
            "matched_objects": [],
            "objects_sampled": 0,
            "metadata_objects_checked": 0,
            "listing_truncated": False
        }},
        "affected": False,
        "affected_reasons": [],
        "warnings": []
    }}

    # ------------------------------------------------------------
    # Actual bucket Region. Never infer Region from ListBuckets.
    # ------------------------------------------------------------
    try:
        location = await call_boto3(
            service_name="s3",
            operation_name="GetBucketLocation",
            region_name="us-east-1",
            params={{"Bucket": bucket_name}}
        )
        bucket_region = _region_from_location(location.get("LocationConstraint"))
        bucket_result["region"] = bucket_region
    except Exception as exc:
        bucket_region = "us-east-1"
        bucket_result["region"] = None
        bucket_result["warnings"].append({{
            "operation": "GetBucketLocation",
            "error": _error_text(exc)
        }})

    # ------------------------------------------------------------
    # Default encryption posture
    # ------------------------------------------------------------
    if config.get("check_encryption"):
        try:
            encryption = await call_boto3(
                service_name="s3",
                operation_name="GetBucketEncryption",
                region_name=bucket_region,
                params={{"Bucket": bucket_name}}
            )
            posture = _encryption_posture(encryption)
            bucket_result["encryption"] = posture

            if posture.get("uses_kms") is not True:
                bucket_result["affected"] = True
                if posture.get("posture") == "SSE_S3":
                    bucket_result["affected_reasons"].append("DEFAULT_ENCRYPTION_NOT_KMS")
                elif posture.get("posture") == "UNKNOWN":
                    bucket_result["affected_reasons"].append("ENCRYPTION_EVIDENCE_UNAVAILABLE")
                else:
                    bucket_result["affected_reasons"].append("DEFAULT_ENCRYPTION_NOT_APPROVED_KMS")
        except Exception as exc:
            bucket_result["encryption"] = {{
                "evidence_status": "UNAVAILABLE",
                "algorithm": None,
                "kms_key_id": None,
                "bucket_key_enabled": None,
                "uses_kms": None,
                "posture": "UNKNOWN"
            }}
            bucket_result["affected"] = True
            bucket_result["affected_reasons"].append("ENCRYPTION_EVIDENCE_UNAVAILABLE")
            bucket_result["warnings"].append({{
                "operation": "GetBucketEncryption",
                "error": _error_text(exc)
            }})

    # ------------------------------------------------------------
    # Public-access posture
    # ------------------------------------------------------------
    if config.get("check_public_access"):
        public_block = None
        policy_public = None
        acl_grants = []
        evidence = {{}}

        try:
            response = await call_boto3(
                service_name="s3",
                operation_name="GetPublicAccessBlock",
                region_name=bucket_region,
                params={{"Bucket": bucket_name}}
            )
            public_block = response.get("PublicAccessBlockConfiguration")
            evidence["public_access_block"] = public_block
        except Exception as exc:
            evidence["public_access_block"] = None
            bucket_result["warnings"].append({{
                "operation": "GetPublicAccessBlock",
                "error": _error_text(exc)
            }})

        try:
            response = await call_boto3(
                service_name="s3",
                operation_name="GetBucketPolicyStatus",
                region_name=bucket_region,
                params={{"Bucket": bucket_name}}
            )
            policy_public = (response.get("PolicyStatus") or {{}}).get("IsPublic")
            evidence["policy_public"] = policy_public
        except Exception as exc:
            evidence["policy_public"] = None
            bucket_result["warnings"].append({{
                "operation": "GetBucketPolicyStatus",
                "error": _error_text(exc)
            }})

        try:
            response = await call_boto3(
                service_name="s3",
                operation_name="GetBucketAcl",
                region_name=bucket_region,
                params={{"Bucket": bucket_name}}
            )
            acl_grants = response.get("Grants", []) or []
            evidence["acl_grants"] = acl_grants
        except Exception as exc:
            evidence["acl_grants"] = []
            bucket_result["warnings"].append({{
                "operation": "GetBucketAcl",
                "error": _error_text(exc)
            }})

        evidence["posture"] = _public_access_posture(
            public_block,
            policy_public,
            acl_grants,
        )
        bucket_result["public_access"] = evidence

        if evidence["posture"] == "PUBLIC":
            bucket_result["affected"] = True
            bucket_result["affected_reasons"].append("PUBLIC_ACCESS_DETECTED")

    # ------------------------------------------------------------
    # Versioning
    # ------------------------------------------------------------
    if config.get("check_versioning"):
        try:
            response = await call_boto3(
                service_name="s3",
                operation_name="GetBucketVersioning",
                region_name=bucket_region,
                params={{"Bucket": bucket_name}}
            )
            bucket_result["versioning"] = {{
                "status": response.get("Status"),
                "mfa_delete": response.get("MFADelete")
            }}
            if response.get("Status") != "Enabled":
                bucket_result["affected"] = True
                bucket_result["affected_reasons"].append("VERSIONING_NOT_ENABLED")
        except Exception as exc:
            bucket_result["warnings"].append({{
                "operation": "GetBucketVersioning",
                "error": _error_text(exc)
            }})

    # ------------------------------------------------------------
    # Server access logging
    # ------------------------------------------------------------
    if config.get("check_logging"):
        try:
            response = await call_boto3(
                service_name="s3",
                operation_name="GetBucketLogging",
                region_name=bucket_region,
                params={{"Bucket": bucket_name}}
            )
            enabled = response.get("LoggingEnabled")
            bucket_result["logging"] = {{
                "enabled": enabled is not None,
                "target_bucket": (enabled or {{}}).get("TargetBucket")
            }}
            if enabled is None:
                bucket_result["affected"] = True
                bucket_result["affected_reasons"].append("SERVER_ACCESS_LOGGING_DISABLED")
        except Exception as exc:
            bucket_result["warnings"].append({{
                "operation": "GetBucketLogging",
                "error": _error_text(exc)
            }})

    # ------------------------------------------------------------
    # Bounded object-name / prefix / metadata sensitivity heuristic.
    # Never download object content. To avoid expensive account-wide object
    # inspection, prioritize buckets already affected by encryption findings.
    # ------------------------------------------------------------
    if config.get("check_sensitive_indicators"):
        indicator = bucket_result["sensitive_data_indicators"]

        # If encryption was part of the question, sensitivity analysis is only
        # needed for buckets that already require encryption review. This keeps
        # account-wide audits bounded when an account contains many buckets.
        should_scan_sensitive = (
            not config.get("check_encryption")
            or bucket_result.get("affected") is True
        )

        if not should_scan_sensitive:
            indicator["status"] = "SKIPPED_NOT_AFFECTED"
            indicator["level"] = "NOT_ASSESSED"
            indicator["basis"] = (
                "Sensitivity sampling was skipped because the bucket did not "
                "require review for the requested encryption control."
            )
        else:
            indicator["status"] = "CHECKED"

        try:
            if not should_scan_sensitive:
                raise StopAsyncIteration()

            response = await call_boto3(
                service_name="s3",
                operation_name="ListObjectsV2",
                region_name=bucket_region,
                params={{
                    "Bucket": bucket_name,
                    "MaxKeys": int(config.get("max_object_keys_per_bucket", 100))
                }}
            )

            contents = response.get("Contents", []) or []
            indicator["objects_sampled"] = len(contents)
            indicator["listing_truncated"] = bool(response.get("IsTruncated"))

            matched_terms = set()
            matched_objects = []
            priority_keys = []

            for item in contents:
                key = str(item.get("Key") or "")
                lower_key = key.lower()
                terms = [term for term in sensitive_terms if term in lower_key]
                if terms:
                    matched_terms.update(terms)
                    priority_keys.append(key)
                    if len(matched_objects) < int(config.get("max_matched_objects_returned", 20)):
                        matched_objects.append({{
                            "key": key,
                            "source": "OBJECT_NAME_OR_PREFIX",
                            "matched_terms": terms
                        }})

            # Check metadata for a small, deterministic sample. Sensitive-looking
            # keys are checked first, then remaining listed keys.
            ordered_keys = []
            seen_keys = set()
            for key in priority_keys + [str(item.get("Key") or "") for item in contents]:
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    ordered_keys.append(key)

            for key in ordered_keys[:int(config.get("max_metadata_objects_per_bucket", 3))]:
                try:
                    head = await call_boto3(
                        service_name="s3",
                        operation_name="HeadObject",
                        region_name=bucket_region,
                        params={{"Bucket": bucket_name, "Key": key}}
                    )
                    indicator["metadata_objects_checked"] += 1
                    metadata = head.get("Metadata", {{}}) or {{}}
                    metadata_text = " ".join(
                        [str(k) for k in metadata.keys()]
                        + [str(v) for v in metadata.values()]
                    ).lower()
                    terms = [term for term in sensitive_terms if term in metadata_text]
                    if terms:
                        matched_terms.update(terms)
                        if len(matched_objects) < int(config.get("max_matched_objects_returned", 20)):
                            matched_objects.append({{
                                "key": key,
                                "source": "USER_METADATA",
                                "matched_terms": terms
                            }})
                except Exception as exc:
                    bucket_result["warnings"].append({{
                        "operation": "HeadObject",
                        "resource": key,
                        "error": _error_text(exc)
                    }})

            indicator["matched_terms"] = sorted(matched_terms)
            indicator["matched_objects"] = matched_objects

            if matched_terms:
                indicator["level"] = "HIGH" if len(matched_terms) >= 3 else "MEDIUM"
                indicator["basis"] = (
                    "Potentially sensitive indicators were found in sampled "
                    "object names, prefixes, or user-defined metadata. Object "
                    "content was not inspected."
                )
            elif indicator["listing_truncated"]:
                indicator["level"] = "UNKNOWN"
                indicator["basis"] = (
                    "No sensitive indicators were found in the bounded sample, "
                    "but the object listing was truncated. Object content was "
                    "not inspected."
                )
            else:
                indicator["level"] = "LOW"
                indicator["basis"] = (
                    "No sensitive indicators were found in the bounded names/"
                    "prefixes/metadata sample. This does not prove that object "
                    "content is non-sensitive."
                )

        except StopAsyncIteration:
            pass
        except Exception as exc:
            indicator["status"] = "UNAVAILABLE"
            indicator["level"] = "UNKNOWN"
            indicator["basis"] = (
                "Object names/prefixes could not be sampled. Object content "
                "was not inspected."
            )
            bucket_result["warnings"].append({{
                "operation": "ListObjectsV2",
                "error": _error_text(exc)
            }})

    if bucket_result["affected"]:
        result["affected_bucket_count"] += 1

    result["buckets"].append(bucket_result)

# Stable ordering helps audit evidence diffing and deterministic UI output.
result["buckets"] = sorted(
    result["buckets"],
    key=lambda item: str(item.get("name") or "")
)

result
'''

    @staticmethod
    def _find_result(value: Any) -> dict[str, Any] | None:
        if isinstance(value, dict):
            if (
                value.get("audit_type") == "S3_SECURITY_AUDIT"
                and isinstance(value.get("buckets"), list)
            ):
                return value

            for child in value.values():
                found = S3SecurityAuditExecutor._find_result(child)
                if found:
                    return found

        elif isinstance(value, list):
            for child in value:
                found = S3SecurityAuditExecutor._find_result(child)
                if found:
                    return found

        return None
