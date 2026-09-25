from __future__ import annotations

from typing import Any


def _safe(value: Any, default: str = "-") -> str:
    if value is None or value == "":
        return default
    return str(value)


def _encryption_label(bucket: dict[str, Any]) -> str:
    encryption = bucket.get("encryption") or {}
    posture = encryption.get("posture")
    if posture == "SSE_KMS":
        return "SSE-KMS"
    if posture == "DSSE_KMS":
        return "DSSE-KMS"
    if posture == "SSE_S3":
        return "SSE-S3"
    if posture == "OTHER":
        return _safe(encryption.get("algorithm"), "Other")
    return "Unknown"


def _recommendation(bucket: dict[str, Any]) -> str:
    reasons = set(bucket.get("affected_reasons") or [])
    encryption = bucket.get("encryption") or {}

    recommendations: list[str] = []

    if (
        "DEFAULT_ENCRYPTION_NOT_KMS" in reasons
        or "DEFAULT_ENCRYPTION_NOT_APPROVED_KMS" in reasons
    ):
        recommendations.append(
            "Configure bucket default encryption with SSE-KMS (aws:kms) "
            "or DSSE-KMS using an approved KMS key; enable an S3 Bucket Key "
            "where appropriate to reduce KMS request cost."
        )

    if "ENCRYPTION_EVIDENCE_UNAVAILABLE" in reasons:
        recommendations.append(
            "Grant the audit role s3:GetEncryptionConfiguration and rerun the "
            "audit before making a compliance conclusion."
        )

    if "PUBLIC_ACCESS_DETECTED" in reasons:
        recommendations.append(
            "Remove unintended public policy/ACL access and enable S3 Block "
            "Public Access unless public access is explicitly required."
        )

    if "VERSIONING_NOT_ENABLED" in reasons:
        recommendations.append(
            "Enable S3 Versioning where the workload requires recovery from "
            "accidental overwrite or deletion."
        )

    if "SERVER_ACCESS_LOGGING_DISABLED" in reasons:
        recommendations.append(
            "Enable an approved S3 access-logging or equivalent audit-logging "
            "control when required by the organization's monitoring policy."
        )

    if encryption.get("uses_kms") is True and not recommendations:
        recommendations.append(
            "No encryption remediation is indicated by the collected bucket "
            "default-encryption evidence."
        )

    return " ".join(recommendations) or "Review the collected evidence and organizational policy."



def _risk_summary(bucket: dict[str, Any]) -> str:
    reasons = set(bucket.get("affected_reasons") or [])
    indicator = bucket.get("sensitive_data_indicators") or {}
    sensitivity = str(indicator.get("level") or "UNKNOWN").upper()

    parts: list[str] = []

    if "PUBLIC_ACCESS_DETECTED" in reasons:
        parts.append(
            "Public access can expose bucket data to unauthorized principals."
        )

    if (
        "DEFAULT_ENCRYPTION_NOT_KMS" in reasons
        or "DEFAULT_ENCRYPTION_NOT_APPROVED_KMS" in reasons
    ):
        parts.append(
            "Data is encrypted at rest, but the bucket default does not use "
            "AWS KMS, so KMS key-policy control, key-level auditability and "
            "customer-managed key governance are not available for that default."
        )

    if "ENCRYPTION_EVIDENCE_UNAVAILABLE" in reasons:
        parts.append(
            "The audit cannot establish the configured bucket-default encryption "
            "because encryption evidence was unavailable."
        )

    if sensitivity in {"HIGH", "MEDIUM"}:
        parts.append(
            f"The sampled object names/prefixes/metadata show {sensitivity.lower()} "
            "potential sensitivity indicators, increasing the impact if access or "
            "encryption controls are weaker than required."
        )

    if "VERSIONING_NOT_ENABLED" in reasons:
        parts.append(
            "Versioning is not enabled, which can reduce recovery options after "
            "accidental overwrite or deletion."
        )

    if "SERVER_ACCESS_LOGGING_DISABLED" in reasons:
        parts.append(
            "Server access logging is not enabled, which can reduce evidence "
            "available for access monitoring and incident investigation."
        )

    return " ".join(parts) or "No additional risk statement was derived from the collected evidence."

def generate_s3_audit_answer(
    *,
    audit_result: dict[str, Any],
    question: str,
) -> str:
    """
    Deterministic audit summary. No LLM is required after evidence collection,
    so provider formatting failures cannot hide a completed S3 audit.
    """

    buckets = audit_result.get("buckets") or []
    requirements = audit_result.get("requirements") or {}

    inventory_requested = bool(requirements.get("check_inventory"))
    encryption_requested = bool(requirements.get("check_encryption"))
    public_requested = bool(requirements.get("check_public_access"))
    sensitive_requested = bool(requirements.get("check_sensitive_indicators"))
    posture_requested = any((encryption_requested, public_requested, sensitive_requested, bool(requirements.get("check_versioning")), bool(requirements.get("check_logging"))))

    # For an encryption-focused question, show KMS exceptions plus unknown
    # evidence. For a broader security question, show every affected bucket.
    if encryption_requested:
        affected = [
            bucket
            for bucket in buckets
            if (
                (bucket.get("encryption") or {}).get("uses_kms") is not True
                or "PUBLIC_ACCESS_DETECTED" in (bucket.get("affected_reasons") or [])
            )
        ]
    else:
        affected = [bucket for bucket in buckets if bucket.get("affected")]

    lines: list[str] = []

    if inventory_requested and not posture_requested:
        lines.append("### S3 bucket inventory")
        lines.append("")
        lines.append(f"Found **{len(buckets)} unique bucket(s)**. Each bucket Region was resolved with `GetBucketLocation`; `ListBuckets` was executed only once.")
        lines.append("")
        lines.append("| Bucket | Region | Creation date |")
        lines.append("| --- | --- | --- |")
        for bucket in buckets:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _safe(bucket.get("name")),
                        _safe(bucket.get("region"), "Unknown"),
                        _safe(bucket.get("creation_date"), "-"),
                    ]
                )
                + " |"
            )
        return "\n".join(lines).strip()

    lines.append("### S3 security audit")
    lines.append("")
    lines.append(
        f"Checked **{len(buckets)} unique bucket(s)**. "
        f"**{len(affected)} bucket(s)** require review for the requested controls."
    )
    lines.append("")

    if not affected:
        lines.append(
            "No affected bucket was identified from the evidence collected for "
            "this request."
        )
    else:
        headers = ["Bucket", "Region"]
        if encryption_requested:
            headers.extend(["Default encryption", "KMS"])
        if public_requested:
            headers.append("Public access")
        if sensitive_requested:
            headers.append("Sensitive indicator")
        headers.append("Finding")

        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        for bucket in affected:
            row = [
                _safe(bucket.get("name")),
                _safe(bucket.get("region"), "Unknown"),
            ]

            if encryption_requested:
                encryption = bucket.get("encryption") or {}
                row.extend(
                    [
                        _encryption_label(bucket),
                        (
                            "Yes"
                            if encryption.get("uses_kms") is True
                            else "No"
                            if encryption.get("uses_kms") is False
                            else "Unknown"
                        ),
                    ]
                )

            if public_requested:
                row.append(
                    _safe((bucket.get("public_access") or {}).get("posture"), "Unknown")
                )

            if sensitive_requested:
                indicator = bucket.get("sensitive_data_indicators") or {}
                row.append(_safe(indicator.get("level"), "Unknown"))

            reasons = bucket.get("affected_reasons") or []
            row.append(", ".join(reasons) if reasons else "Review")
            lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")

        lines.append("")
        lines.append("### Affected bucket details")
        lines.append("")

        for bucket in affected:
            name = _safe(bucket.get("name"))
            lines.append(f"**{name}**")

            if encryption_requested:
                encryption = bucket.get("encryption") or {}
                lines.append(
                    f"- Encryption evidence: **{_encryption_label(bucket)}**; "
                    f"KMS key: `{_safe(encryption.get('kms_key_id'), 'not reported')}`; "
                    f"Bucket Key: `{_safe(encryption.get('bucket_key_enabled'), 'unknown')}`."
                )

            if public_requested:
                public = bucket.get("public_access") or {}
                lines.append(
                    f"- Public-access posture: **{_safe(public.get('posture'), 'Unknown')}**."
                )

            if sensitive_requested:
                indicator = bucket.get("sensitive_data_indicators") or {}
                matched_terms = indicator.get("matched_terms") or []
                matched_objects = indicator.get("matched_objects") or []
                lines.append(
                    f"- Potential sensitive-data indicator: **{_safe(indicator.get('level'), 'Unknown')}**. "
                    f"{_safe(indicator.get('basis'), '')}"
                )
                if matched_terms:
                    lines.append(
                        "- Matched heuristic terms: "
                        + ", ".join(f"`{term}`" for term in matched_terms[:12])
                        + "."
                    )
                if matched_objects:
                    sample_names = [
                        _safe(item.get("key"))
                        for item in matched_objects[:5]
                    ]
                    lines.append(
                        "- Example matched object keys: "
                        + ", ".join(f"`{key}`" for key in sample_names)
                        + "."
                    )

            lines.append(f"- Risk: {_risk_summary(bucket)}")
            lines.append(f"- Recommendation: {_recommendation(bucket)}")
            lines.append("")

    if sensitive_requested:
        lines.append(
            "**Sensitivity limitation:** this is a heuristic based on a bounded "
            "sample of object names, prefixes and user-defined metadata. Object "
            "content was not downloaded or inspected, so a LOW result does not "
            "prove that the bucket contains no sensitive data."
        )
        lines.append("")

    if encryption_requested:
        lines.append(
            "**Encryption interpretation:** `SSE-S3` means objects are encrypted "
            "at rest but the bucket default is not using AWS KMS. Missing or "
            "inaccessible encryption evidence is reported as **Unknown**, not as "
            "\"encryption disabled\"."
        )

    return "\n".join(lines).strip()
