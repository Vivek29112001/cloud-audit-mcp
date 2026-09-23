from __future__ import annotations

from typing import Any


def _norm(value: object) -> str:
    return str(value or "").strip().lower()


def _unique(values: list[object]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _context_label(evidence: dict[str, Any]) -> str:
    context = evidence.get("selected_context") or {}
    return str(
        context.get("label")
        or context.get("billing_service")
        or context.get("service")
        or context.get("resource_id")
        or context.get("region")
        or "the selected AWS context"
    ).strip()


def _service_rows(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    classification = evidence.get("classification") or {}
    rows: list[dict[str, Any]] = []
    for bucket in (
        "primary_paid_services",
        "zero_cost_services",
        "supporting_services",
        "discovered_unbilled_services",
        "billing_only_services",
        "non_positive_billing_services",
    ):
        for item in classification.get(bucket) or []:
            if isinstance(item, dict):
                rows.append(item)
    return rows


def try_generate_snapshot_answer(
    *,
    question: str,
    snapshot_evidence: dict[str, Any],
) -> str | None:
    """
    Deterministically answer common saved-snapshot inventory questions.

    This is intentionally service-agnostic: it never contains an EC2/RDS/S3
    allowlist or mapping. It only formats evidence already present in the
    immutable persisted scan.
    """
    q = _norm(question)
    evidence = snapshot_evidence
    label = _context_label(evidence)
    context = evidence.get("selected_context") or {}
    scan_time = evidence.get("scan_completed_at") or evidence.get("scan_started_at")
    snapshot_suffix = f" in the saved scan from {scan_time}" if scan_time else " in the saved scan"

    # ---------------------------------------------------------
    # Region questions for a selected service/resource/context
    # ---------------------------------------------------------
    if "region" in q:
        candidates: list[object] = []
        candidates.extend(context.get("regions") or [])

        resources = evidence.get("resources") or {}
        for item in resources.get("matching_resources") or []:
            if isinstance(item, dict):
                candidates.append(item.get("region"))

        for item in _service_rows(evidence):
            candidates.extend(item.get("regions") or [])

        # When a region itself is selected, preserve it as evidence.
        if context.get("region"):
            candidates.append(context.get("region"))

        regions = _unique(candidates)
        if regions:
            return (
                f"{label} was associated with {len(regions)} AWS Region"
                f"{'s' if len(regions) != 1 else ''}{snapshot_suffix}: "
                + ", ".join(regions)
                + "."
            )

        return (
            f"The saved snapshot does not contain Region evidence for {label}. "
            "A refresh or live read-only query may be needed for current Region data."
        )

    # ---------------------------------------------------------
    # Resource listing/count questions
    # ---------------------------------------------------------
    if any(term in q for term in ("resource", "resources")):
        resources = evidence.get("resources") or {}
        rows = [item for item in resources.get("matching_resources") or [] if isinstance(item, dict)]
        total = resources.get("matching_resource_count")
        if rows:
            identifiers = _unique([
                item.get("resource_id") or item.get("arn") or item.get("resource_type")
                for item in rows
            ])
            prefix = f"{label} has {total if total is not None else len(rows)} matching resource(s){snapshot_suffix}."
            if identifiers:
                return prefix + " Resources shown: " + ", ".join(identifiers) + "."
            return prefix
        if total == 0:
            return f"No matching resources for {label} were recorded{snapshot_suffix}."

    # ---------------------------------------------------------
    # Billing / cost questions
    # ---------------------------------------------------------
    if any(term in q for term in ("cost", "billing", "bill", "spend", "price")):
        billing = evidence.get("billing") or {}
        service_costs = [item for item in billing.get("service_costs") or [] if isinstance(item, dict)]
        context_billing = _norm(context.get("billing_service"))
        if context_billing:
            service_costs = [
                item for item in service_costs
                if _norm(item.get("billing_service")) == context_billing
            ]
        if service_costs:
            parts: list[str] = []
            for item in service_costs[:10]:
                name = item.get("billing_service") or label
                amount = item.get("amount")
                if amount is None:
                    amount = item.get("cost")
                currency = item.get("unit") or item.get("currency") or billing.get("currency") or ""
                parts.append(f"{name}: {amount} {currency}".strip())
            return "Saved-snapshot billing evidence: " + "; ".join(parts) + "."

        if billing.get("total_cost") is not None and not context.get("service"):
            return (
                f"The saved scan billing total is {billing.get('total_cost')} "
                f"{billing.get('currency') or ''}.".strip()
            )

    # ---------------------------------------------------------
    # Service list questions without a selected service
    # ---------------------------------------------------------
    if "service" in q and any(term in q for term in ("list", "show", "which", "what")):
        detected = (evidence.get("resources") or {}).get("detected_services") or []
        names = _unique([
            item.get("service") if isinstance(item, dict) else item
            for item in detected
        ])
        if names:
            return (
                f"The saved scan contains {len(names)} resource-backed AWS service(s): "
                + ", ".join(names)
                + "."
            )

    return None
