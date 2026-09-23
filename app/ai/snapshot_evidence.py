from __future__ import annotations

from datetime import date, datetime
from typing import Any


# Keep snapshot prompts bounded. The persisted scan remains complete in SQLite;
# these limits only control how much evidence is sent to the NLP formatter.
MAX_RESOURCE_EVIDENCE = 20
MAX_SERVICE_EVIDENCE = 35
MAX_REGION_EVIDENCE = 25
MAX_ZONE_EVIDENCE = 40
MAX_RELATIONSHIP_EVIDENCE = 30
MAX_BILLING_COMPONENT_EVIDENCE = 15
MAX_WARNING_EVIDENCE = 20


def _norm(value: object) -> str:
    return str(value or "").strip().lower()


def _json_safe(value: Any) -> Any:
    """Convert nested snapshot data into JSON-native values."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value




def _compact_json(
    value: Any,
    *,
    depth: int = 0,
    max_depth: int = 5,
    max_items: int = 50,
    max_string: int = 1800,
) -> Any:
    """Bound arbitrarily large Resource Explorer property payloads."""
    if depth >= max_depth:
        if isinstance(value, (dict, list, tuple, set)):
            return "<nested data omitted>"
        return value
    if isinstance(value, str):
        if len(value) <= max_string:
            return value
        return value[:max_string] + "…<truncated>"
    if isinstance(value, dict):
        items = list(value.items())
        result = {
            str(key): _compact_json(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                max_items=max_items,
                max_string=max_string,
            )
            for key, item in items[:max_items]
        }
        if len(items) > max_items:
            result["_truncated_fields"] = len(items) - max_items
        return result
    if isinstance(value, (list, tuple, set)):
        values = list(value)
        result = [
            _compact_json(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                max_items=max_items,
                max_string=max_string,
            )
            for item in values[:max_items]
        ]
        if len(values) > max_items:
            result.append({"_truncated_items": len(values) - max_items})
        return result
    return value


def _bounded(values: Any, limit: int) -> tuple[list[Any], bool]:
    if not isinstance(values, list):
        return [], False
    return values[:limit], len(values) > limit


def _matches_service(item: dict[str, Any], service: str) -> bool:
    if not service:
        return True
    target = _norm(service)
    candidates = [
        item.get("service"),
        item.get("service_namespace"),
        item.get("discovered_service"),
        item.get("key"),
        item.get("billing_service"),
    ]
    candidates.extend(item.get("billing_services") or [])
    return any(target == _norm(value) for value in candidates if value)


def _matches_resource(item: dict[str, Any], resource_id: str) -> bool:
    if not resource_id:
        return True
    target = _norm(resource_id)
    return target in {
        _norm(item.get("resource_id")),
        _norm(item.get("arn")),
    }


def _compact_classified_service(item: dict[str, Any]) -> dict[str, Any]:
    """Keep only fields needed for audit/NLP service answers."""
    keys = (
        "key",
        "category",
        "paid",
        "financial_status",
        "billing_amount",
        "currency",
        "billing_services",
        "discovered_service",
        "resource_count",
        "regions",
        "related_primary_services",
        "billing_match_method",
        "billing_match_confidence",
    )
    return {key: item.get(key) for key in keys if item.get(key) is not None}


def _compact_resource(item: dict[str, Any], *, include_properties: bool) -> dict[str, Any]:
    result = {
        key: item.get(key)
        for key in (
            "arn",
            "resource_id",
            "resource_type",
            "service",
            "region",
            "owning_account_id",
        )
        if item.get(key) is not None
    }
    if include_properties:
        properties = item.get("properties") or []
        if isinstance(properties, list):
            result["properties"] = properties[:8]
            result["properties_truncated"] = len(properties) > 8
    return result


def _filter_service_rows(values: Any, target: str) -> list[dict[str, Any]]:
    rows = [item for item in (values or []) if isinstance(item, dict)]
    if target:
        rows = [item for item in rows if _matches_service(item, target)]
    return rows


def build_snapshot_evidence(
    *,
    scan_result: dict[str, Any],
    selected_context: dict[str, Any] | None,
    intent: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Build compact, JSON-safe evidence from one immutable persisted scan.

    The database keeps the full scan. This function intentionally avoids sending
    the complete inventory/billing payload to Groq on every chat question.
    """
    context = dict(selected_context or {})
    intent = dict(intent or {})

    service = str(
        context.get("service")
        or context.get("service_namespace")
        or intent.get("service")
        or ""
    ).strip()
    billing_service = str(context.get("billing_service") or "").strip()
    service_target = service or billing_service
    resource_id = str(
        context.get("resource_id")
        or context.get("arn")
        or intent.get("resource_id")
        or ""
    ).strip()
    region = str(context.get("region") or intent.get("region") or "").strip()

    # ---------------------------------------------------------
    # Resources
    # ---------------------------------------------------------
    resources_section = scan_result.get("resources") or {}
    all_resources = [
        item
        for item in (resources_section.get("resources") or [])
        if isinstance(item, dict)
    ]

    matching_resources: list[dict[str, Any]] = []
    for item in all_resources:
        if service and not _matches_service(item, service):
            continue
        if resource_id and not _matches_resource(item, resource_id):
            continue
        if region and _norm(item.get("region")) != _norm(region):
            continue
        matching_resources.append(item)

    # A generic account/service-summary question does not need hundreds of raw
    # resource objects. Include a small sample only; selected-resource/service
    # questions get their filtered rows.
    if service or resource_id or region:
        raw_resource_rows = matching_resources[:MAX_RESOURCE_EVIDENCE]
        resource_rows = [
            _compact_resource(
                item,
                include_properties=bool(resource_id),
            )
            for item in raw_resource_rows
        ]
        resource_truncated = len(matching_resources) > MAX_RESOURCE_EVIDENCE
        matching_count = len(matching_resources)
    else:
        raw_resource_rows = all_resources[:5]
        resource_rows = [
            _compact_resource(item, include_properties=False)
            for item in raw_resource_rows
        ]
        resource_truncated = len(all_resources) > len(resource_rows)
        matching_count = len(all_resources)

    detected_services, detected_services_truncated = _bounded(
        resources_section.get("detected_services") or [],
        MAX_SERVICE_EVIDENCE,
    )

    # ---------------------------------------------------------
    # Classification
    # ---------------------------------------------------------
    classification = scan_result.get("classification") or {}
    classification_view: dict[str, Any] = {
        "billing_available": classification.get("billing_available"),
    }

    for bucket in (
        "primary_paid_services",
        "zero_cost_services",
        "supporting_services",
        "discovered_unbilled_services",
        "billing_only_services",
        "non_positive_billing_services",
    ):
        rows = _filter_service_rows(classification.get(bucket) or [], service_target)
        limited = rows[:MAX_SERVICE_EVIDENCE]
        classification_view[bucket] = [
            _compact_classified_service(item) for item in limited
        ]
        classification_view[f"{bucket}_truncated"] = len(rows) > len(limited)

    for bucket in (
        "paid_regions",
        "used_unbilled_regions",
        "enabled_unused_regions",
        "billed_only_regions",
    ):
        rows = [item for item in (classification.get(bucket) or []) if isinstance(item, dict)]
        if region:
            rows = [item for item in rows if _norm(item.get("region")) == _norm(region)]
        limited = rows[:MAX_REGION_EVIDENCE]
        classification_view[bucket] = limited
        classification_view[f"{bucket}_truncated"] = len(rows) > len(limited)

    relationships = [
        item for item in (classification.get("relationships") or []) if isinstance(item, dict)
    ]
    if service or resource_id:
        target_service = _norm(service)
        target_resource = _norm(resource_id)
        filtered_relationships: list[dict[str, Any]] = []
        for item in relationships:
            service_hit = target_service and target_service in {
                _norm(item.get("source_service")),
                _norm(item.get("target_service")),
            }
            resource_hit = target_resource and target_resource in {
                _norm(item.get("source_resource_id")),
                _norm(item.get("source_arn")),
                _norm(item.get("target_resource_id")),
                _norm(item.get("target_arn")),
            }
            if service_hit or resource_hit:
                filtered_relationships.append(item)
        relationships = filtered_relationships
    else:
        # Relationship details are expensive and rarely needed for a generic
        # account question. Keep only a tiny sample for situational awareness.
        relationships = relationships[:5]

    classification_view["relationships"] = relationships[:MAX_RELATIONSHIP_EVIDENCE]
    classification_view["relationships_truncated"] = (
        len(relationships) > MAX_RELATIONSHIP_EVIDENCE
    )

    # ---------------------------------------------------------
    # Billing
    # ---------------------------------------------------------
    billing = scan_result.get("billing") or {}
    service_costs = [
        item for item in (billing.get("service_costs") or []) if isinstance(item, dict)
    ]
    if billing_service:
        service_costs = [
            item
            for item in service_costs
            if _norm(item.get("billing_service")) == _norm(billing_service)
        ]

    region_costs = [
        item for item in (billing.get("region_costs") or []) if isinstance(item, dict)
    ]
    if region:
        region_costs = [
            item for item in region_costs if _norm(item.get("region")) == _norm(region)
        ]

    # Usage-type components can be very large. Only send them when a billing
    # service is explicitly selected; otherwise the service totals are enough.
    components: list[dict[str, Any]] = []
    components_truncated = False
    if billing_service or service:
        raw_components = [
            item for item in (billing.get("components") or []) if isinstance(item, dict)
        ]
        target = billing_service
        if not target and service:
            matched_billing_names: set[str] = set()
            for bucket in (
                "primary_paid_services",
                "zero_cost_services",
                "supporting_services",
                "discovered_unbilled_services",
            ):
                for item in _filter_service_rows(classification.get(bucket) or [], service):
                    matched_billing_names.update(
                        str(name).strip()
                        for name in (item.get("billing_services") or [])
                        if str(name).strip()
                    )
            if matched_billing_names:
                raw_components = [
                    item
                    for item in raw_components
                    if str(item.get("billing_service") or "").strip() in matched_billing_names
                ]
        elif target:
            raw_components = [
                item
                for item in raw_components
                if _norm(item.get("billing_service")) == _norm(target)
            ]
        components = raw_components[:MAX_BILLING_COMPONENT_EVIDENCE]
        components_truncated = len(raw_components) > len(components)

    billing_view = {
        "available": billing.get("available"),
        "period_start": billing.get("period_start"),
        "period_end_exclusive": billing.get("period_end_exclusive"),
        "metric": billing.get("metric"),
        "currency": billing.get("currency"),
        "total_cost": billing.get("total_cost"),
        "service_costs": service_costs[:MAX_SERVICE_EVIDENCE],
        "service_costs_truncated": len(service_costs) > MAX_SERVICE_EVIDENCE,
        "region_costs": region_costs[:MAX_REGION_EVIDENCE],
        "region_costs_truncated": len(region_costs) > MAX_REGION_EVIDENCE,
        "components": components,
        "components_truncated": components_truncated,
        "warnings": (billing.get("warnings") or [])[:MAX_WARNING_EVIDENCE],
    }

    # ---------------------------------------------------------
    # Regions and zones
    # ---------------------------------------------------------
    regions = scan_result.get("regions") or {}
    region_rows = [item for item in (regions.get("regions") or []) if isinstance(item, dict)]
    if region:
        region_rows = [
            item for item in region_rows if _norm(item.get("region_name")) == _norm(region)
        ]
    regions_view = {
        "total_regions": regions.get("total_regions"),
        "enabled_regions": regions.get("enabled_regions"),
        "disabled_regions": regions.get("disabled_regions"),
        "regions": region_rows[:MAX_REGION_EVIDENCE],
        "regions_truncated": len(region_rows) > MAX_REGION_EVIDENCE,
    }

    zones = scan_result.get("zones") or {}
    zone_rows = [item for item in (zones.get("zones") or []) if isinstance(item, dict)]
    if region:
        zone_rows = [
            item for item in zone_rows if _norm(item.get("region_name")) == _norm(region)
        ]
    zones_view = {
        "total_zones": zones.get("total_zones"),
        "zones": zone_rows[:MAX_ZONE_EVIDENCE],
        "zones_truncated": len(zone_rows) > MAX_ZONE_EVIDENCE,
    }

    evidence = {
        "evidence_source": "PERSISTED_DISCOVERY_SNAPSHOT",
        "scan_id": scan_result.get("scan_id"),
        "scan_status": scan_result.get("status"),
        "scan_started_at": scan_result.get("started_at"),
        "scan_completed_at": scan_result.get("completed_at"),
        "selected_context": context,
        "account": scan_result.get("account") or {},
        "summary": scan_result.get("summary") or {},
        "regions": regions_view,
        "zones": zones_view,
        "resources": {
            "total_resources": resources_section.get("total_resources", 0),
            "used_regions": resources_section.get("used_regions") or [],
            "detected_services": detected_services,
            "detected_services_truncated": detected_services_truncated,
            "matching_resources": resource_rows,
            "matching_resource_count": matching_count,
            "resource_evidence_truncated": resource_truncated,
        },
        "billing": billing_view,
        "classification": classification_view,
        "scan_warnings": (scan_result.get("warnings") or [])[:MAX_WARNING_EVIDENCE],
    }
    return _compact_json(_json_safe(evidence))
