# from __future__ import annotations

# import re
# from collections import defaultdict
# from difflib import SequenceMatcher
# from typing import Any, Iterable

# from app.providers.aws.models import (
#     AWSBillingComponent,
#     AWSBillingDiscoveryResult,
#     AWSClassifiedRegion,
#     AWSClassifiedService,
#     AWSInfrastructureClassificationResult,
#     AWSRegionDiscoveryResult,
#     AWSResource,
#     AWSResourceDiscoveryResult,
#     AWSResourceRelationship,
# )


# class AWSInfrastructureClassificationService:
#     """
#     Evidence-based service and Region classification.

#     No service-name lookup table or Region catalog is embedded here.
#     Classification comes from:
#       1. Cost Explorer billing values,
#       2. Resource Explorer inventory,
#       3. references between discovered resource properties.

#     "Primary" follows the caller's requested business definition: a service or
#     Region with positive UnblendedCost in the current billing window.
#     "Supporting" means a discovered, non-paid service with a data-derived
#     resource relationship to a paid discovered service.
#     """

#     COST_EPSILON = 1e-9

#     def classify(
#         self,
#         *,
#         regions: AWSRegionDiscoveryResult,
#         resources: AWSResourceDiscoveryResult,
#         billing: AWSBillingDiscoveryResult,
#     ) -> AWSInfrastructureClassificationResult:
#         relationships = self._discover_relationships(resources.resources)
#         service_result = self._classify_services(
#             resources=resources,
#             billing=billing,
#             relationships=relationships,
#         )
#         region_result = self._classify_regions(
#             regions=regions,
#             resources=resources,
#             billing=billing,
#         )

#         warnings = list(billing.warnings)
#         if billing.available and not billing.service_costs:
#             warnings.append(
#                 "Cost Explorer was reachable but returned no SERVICE cost groups "
#                 "for the selected billing window."
#             )

#         return AWSInfrastructureClassificationResult(
#             billing_available=billing.available,
#             primary_paid_services=service_result["primary"],
#             supporting_services=service_result["supporting"],
#             discovered_unbilled_services=service_result["unbilled"],
#             non_positive_billing_services=service_result["non_positive"],
#             paid_regions=region_result["paid"],
#             used_unbilled_regions=region_result["used_unbilled"],
#             enabled_unused_regions=region_result["enabled_unused"],
#             billed_only_regions=region_result["billed_only"],
#             relationships=relationships,
#             warnings=warnings,
#         )

#     def _classify_services(
#         self,
#         *,
#         resources: AWSResourceDiscoveryResult,
#         billing: AWSBillingDiscoveryResult,
#         relationships: list[AWSResourceRelationship],
#     ) -> dict[str, list[AWSClassifiedService]]:
#         discovered = {
#             item.service.strip().lower(): item
#             for item in resources.detected_services
#             if item.service.strip()
#         }

#         # billing service -> best dynamically inferred discovered service
#         billing_matches: dict[str, tuple[str, str, float] | None] = {}
#         for cost in billing.service_costs:
#             billing_matches[cost.billing_service] = self._best_service_match(
#                 billing_name=cost.billing_service,
#                 discovered_services=discovered.keys(),
#             )

#         matched_costs: dict[str, list[Any]] = defaultdict(list)
#         unmatched_costs: list[Any] = []

#         for cost in billing.service_costs:
#             match = billing_matches.get(cost.billing_service)
#             if match is None:
#                 unmatched_costs.append(cost)
#                 continue
#             matched_costs[match[0]].append(cost)

#         components_by_billing: dict[str, list[AWSBillingComponent]] = defaultdict(list)
#         for component in billing.components:
#             components_by_billing[component.billing_service].append(component)

#         paid_discovered: set[str] = set()
#         discovered_amounts: dict[str, float] = {}

#         for service, costs in matched_costs.items():
#             amount = sum(item.amount for item in costs)
#             discovered_amounts[service] = amount
#             if amount > self.COST_EPSILON:
#                 paid_discovered.add(service)

#         adjacency: dict[str, set[str]] = defaultdict(set)
#         for edge in relationships:
#             left = (edge.source_service or "").strip().lower()
#             right = (edge.target_service or "").strip().lower()
#             if not left or not right or left == right:
#                 continue
#             adjacency[left].add(right)
#             adjacency[right].add(left)

#         primary: list[AWSClassifiedService] = []
#         supporting: list[AWSClassifiedService] = []
#         unbilled: list[AWSClassifiedService] = []
#         non_positive: list[AWSClassifiedService] = []

#         for service, discovered_entry in discovered.items():
#             costs = matched_costs.get(service, [])
#             amount = sum(item.amount for item in costs)
#             billing_names = sorted({item.billing_service for item in costs})
#             components = self._components_for_names(
#                 billing_names,
#                 components_by_billing,
#             )

#             match_methods = []
#             match_confidences = []
#             for name in billing_names:
#                 match = billing_matches.get(name)
#                 if match is not None:
#                     match_methods.append(match[1])
#                     match_confidences.append(match[2])

#             related_primary = sorted(
#                 adjacent
#                 for adjacent in adjacency.get(service, set())
#                 if adjacent in paid_discovered
#             )

#             if amount > self.COST_EPSILON:
#                 category = "PRIMARY_PAID"
#             elif related_primary:
#                 category = "SUPPORTING_RELATED"
#             else:
#                 category = "DISCOVERED_UNBILLED"

#             item = AWSClassifiedService(
#                 key=service,
#                 category=category,
#                 paid=amount > self.COST_EPSILON,
#                 billing_amount=amount,
#                 currency=billing.currency,
#                 billing_services=billing_names,
#                 billing_components=components,
#                 discovered_service=service,
#                 resource_count=discovered_entry.resource_count,
#                 regions=discovered_entry.regions,
#                 related_primary_services=related_primary,
#                 billing_match_method=(
#                     ",".join(sorted(set(match_methods))) if match_methods else None
#                 ),
#                 billing_match_confidence=(
#                     max(match_confidences) if match_confidences else None
#                 ),
#             )

#             if category == "PRIMARY_PAID":
#                 primary.append(item)
#             elif category == "SUPPORTING_RELATED":
#                 supporting.append(item)
#             else:
#                 unbilled.append(item)

#         # Positive billing entries are primary even when Resource Explorer did
#         # not expose a matching resource/service. This prevents billing-only
#         # services from disappearing from the audit result.
#         for cost in unmatched_costs:
#             components = self._components_for_names(
#                 [cost.billing_service],
#                 components_by_billing,
#             )
#             item = AWSClassifiedService(
#                 key=f"billing:{self._normalize(cost.billing_service)}",
#                 category=(
#                     "PRIMARY_PAID_BILLING_ONLY"
#                     if cost.amount > self.COST_EPSILON
#                     else "BILLING_NON_POSITIVE"
#                 ),
#                 paid=cost.amount > self.COST_EPSILON,
#                 billing_amount=cost.amount,
#                 currency=cost.unit or billing.currency,
#                 billing_services=[cost.billing_service],
#                 billing_components=components,
#             )
#             if item.paid:
#                 primary.append(item)
#             else:
#                 non_positive.append(item)

#         primary.sort(key=lambda item: (-item.billing_amount, item.key))
#         supporting.sort(key=lambda item: (-item.resource_count, item.key))
#         unbilled.sort(key=lambda item: (-item.resource_count, item.key))
#         non_positive.sort(key=lambda item: (item.billing_amount, item.key))

#         return {
#             "primary": primary,
#             "supporting": supporting,
#             "unbilled": unbilled,
#             "non_positive": non_positive,
#         }

#     def _classify_regions(
#         self,
#         *,
#         regions: AWSRegionDiscoveryResult,
#         resources: AWSResourceDiscoveryResult,
#         billing: AWSBillingDiscoveryResult,
#     ) -> dict[str, list[AWSClassifiedRegion]]:
#         enabled = {
#             item.region_name
#             for item in regions.regions
#             if item.enabled and item.region_name
#         }

#         resource_counts: dict[str, int] = defaultdict(int)
#         for resource in resources.resources:
#             region = (resource.region or "").strip()
#             if region and region.lower() != "global":
#                 resource_counts[region] += 1

#         billing_costs = {
#             item.region: item
#             for item in billing.region_costs
#             if item.region
#         }

#         all_regions = sorted(
#             enabled
#             | set(resource_counts)
#             | set(billing_costs)
#         )

#         result = {
#             "paid": [],
#             "used_unbilled": [],
#             "enabled_unused": [],
#             "billed_only": [],
#         }

#         for region in all_regions:
#             billing_entry = billing_costs.get(region)
#             amount = billing_entry.amount if billing_entry else 0.0
#             unit = billing_entry.unit if billing_entry else billing.currency
#             count = resource_counts.get(region, 0)
#             is_enabled = region in enabled

#             if amount > self.COST_EPSILON:
#                 category = (
#                     "PAID_PRIMARY"
#                     if is_enabled or count > 0
#                     else "PAID_BILLING_ONLY"
#                 )
#                 bucket = "paid"
#             elif count > 0:
#                 category = "USED_UNBILLED"
#                 bucket = "used_unbilled"
#             elif is_enabled:
#                 category = "ENABLED_UNUSED"
#                 bucket = "enabled_unused"
#             else:
#                 category = "BILLING_ONLY_NON_POSITIVE"
#                 bucket = "billed_only"

#             result[bucket].append(
#                 AWSClassifiedRegion(
#                     region=region,
#                     category=category,
#                     billing_amount=amount,
#                     currency=unit,
#                     resource_count=count,
#                     enabled=is_enabled,
#                 )
#             )

#         result["paid"].sort(key=lambda item: (-item.billing_amount, item.region))
#         result["used_unbilled"].sort(key=lambda item: (-item.resource_count, item.region))
#         result["enabled_unused"].sort(key=lambda item: item.region)
#         result["billed_only"].sort(key=lambda item: (item.billing_amount, item.region))
#         return result

#     @staticmethod
#     def _components_for_names(
#         billing_names: Iterable[str],
#         components_by_billing: dict[str, list[AWSBillingComponent]],
#     ) -> list[AWSBillingComponent]:
#         components = [
#             component
#             for name in billing_names
#             for component in components_by_billing.get(name, [])
#         ]
#         components.sort(key=lambda item: (-item.amount, item.usage_type))
#         return components

#     def _best_service_match(
#         self,
#         *,
#         billing_name: str,
#         discovered_services: Iterable[str],
#     ) -> tuple[str, str, float] | None:
#         billing_normalized = self._normalize(billing_name)
#         aliases = self._dynamic_aliases(billing_name)

#         best: tuple[str, str, float] | None = None

#         for service in discovered_services:
#             normalized = self._normalize(service)
#             if not normalized:
#                 continue

#             if normalized in aliases:
#                 candidate = (service, "dynamic_alias", 1.0)
#             elif (
#                 len(normalized) >= 3
#                 and (
#                     normalized in billing_normalized
#                     or billing_normalized in normalized
#                 )
#             ):
#                 candidate = (service, "normalized_substring", 0.92)
#             else:
#                 ratio = SequenceMatcher(
#                     None,
#                     normalized,
#                     billing_normalized,
#                 ).ratio()
#                 if ratio < 0.82:
#                     continue
#                 candidate = (service, "string_similarity", round(ratio, 4))

#             if best is None or candidate[2] > best[2]:
#                 best = candidate

#         return best

#     @classmethod
#     def _dynamic_aliases(cls, value: str) -> set[str]:
#         """
#         Generate aliases from the billing name itself.

#         Examples derived by the algorithm (not a lookup table):
#           Elastic + Compute + Cloud -> e,c,c -> ec2
#           Simple + Storage + Service -> s,s,s -> s3
#           Relational + Database + Service -> rds
#         """
#         tokens = cls._words(value)
#         aliases = {cls._normalize(value)}

#         for token in tokens:
#             aliases.add(cls._normalize(token))

#         max_window = min(len(tokens), 7)
#         for width in range(2, max_window + 1):
#             for start in range(0, len(tokens) - width + 1):
#                 window = tokens[start : start + width]
#                 aliases.add(cls._normalize("".join(window)))
#                 aliases.add(cls._compress_initials(window))

#         return {alias for alias in aliases if alias}

#     @staticmethod
#     def _words(value: str) -> list[str]:
#         # Split camel-case, acronym boundaries, digit suffixes and punctuation.
#         expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
#         expanded = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", expanded)
#         return re.findall(r"[A-Za-z]+\d*|\d+", expanded)

#     @classmethod
#     def _compress_initials(cls, words: list[str]) -> str:
#         initials: list[str] = []
#         for word in words:
#             cleaned = cls._normalize(word)
#             if cleaned:
#                 initials.append(cleaned[0])
#         if not initials:
#             return ""

#         output: list[str] = []
#         index = 0
#         while index < len(initials):
#             current = initials[index]
#             end = index + 1
#             while end < len(initials) and initials[end] == current:
#                 end += 1
#             count = end - index
#             output.append(current)
#             if count > 1:
#                 output.append(str(count))
#             index = end
#         return "".join(output)

#     @staticmethod
#     def _normalize(value: str) -> str:
#         return re.sub(r"[^a-z0-9]+", "", value.lower())

#     def _discover_relationships(
#         self,
#         resources: list[AWSResource],
#     ) -> list[AWSResourceRelationship]:
#         identifiers: dict[str, list[AWSResource]] = defaultdict(list)

#         for resource in resources:
#             for identifier in (resource.arn, resource.resource_id):
#                 normalized = (identifier or "").strip().lower()
#                 if len(normalized) >= 6:
#                     identifiers[normalized].append(resource)

#         relationships: list[AWSResourceRelationship] = []
#         seen_pairs: set[tuple[str, str]] = set()

#         for source in resources:
#             source_key = self._resource_key(source)
#             if not source_key:
#                 continue

#             for scalar in self._flatten_scalars(source.properties):
#                 for candidate in self._reference_candidates(scalar):
#                     for target in identifiers.get(candidate.lower(), []):
#                         target_key = self._resource_key(target)
#                         if not target_key or target_key == source_key:
#                             continue

#                         pair = tuple(sorted((source_key, target_key)))
#                         if pair in seen_pairs:
#                             continue
#                         seen_pairs.add(pair)

#                         relationships.append(
#                             AWSResourceRelationship(
#                                 source_arn=source.arn,
#                                 source_resource_id=source.resource_id,
#                                 source_service=source.service,
#                                 target_arn=target.arn,
#                                 target_resource_id=target.resource_id,
#                                 target_service=target.service,
#                                 evidence=candidate,
#                             )
#                         )

#         relationships.sort(
#             key=lambda item: (
#                 item.source_service or "",
#                 item.source_resource_id or item.source_arn or "",
#                 item.target_service or "",
#                 item.target_resource_id or item.target_arn or "",
#             )
#         )
#         return relationships

#     @classmethod
#     def _flatten_scalars(cls, value: Any) -> list[str]:
#         output: list[str] = []
#         if isinstance(value, dict):
#             for child in value.values():
#                 output.extend(cls._flatten_scalars(child))
#         elif isinstance(value, (list, tuple, set)):
#             for child in value:
#                 output.extend(cls._flatten_scalars(child))
#         elif value is not None:
#             output.append(str(value))
#         return output

#     @staticmethod
#     def _reference_candidates(value: str) -> set[str]:
#         # Extract ARNs and resource-id-shaped tokens from arbitrary property
#         # strings/JSON. No resource prefix catalog is required.
#         matches = re.findall(
#             r"arn:[^\s\"',}\]]+|[A-Za-z0-9][A-Za-z0-9._:/-]{5,}",
#             value,
#         )
#         return {
#             match.rstrip(".,;:)")
#             for match in matches
#             if len(match.rstrip(".,;:)")) >= 6
#         }

#     @staticmethod
#     def _resource_key(resource: AWSResource) -> str | None:
#         if resource.arn:
#             return resource.arn.lower()
#         if resource.resource_id:
#             return (
#                 f"{(resource.service or '').lower()}|"
#                 f"{(resource.region or '').lower()}|"
#                 f"{resource.resource_id.lower()}"
#             )
#         return None




from __future__ import annotations

import re
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Any, Iterable

from app.providers.aws.models import (
    AWSBillingComponent,
    AWSBillingDiscoveryResult,
    AWSClassifiedRegion,
    AWSClassifiedService,
    AWSInfrastructureClassificationResult,
    AWSRegionDiscoveryResult,
    AWSResource,
    AWSResourceDiscoveryResult,
    AWSResourceRelationship,
)


class AWSInfrastructureClassificationService:
    """
    Evidence-based service and Region classification.

    No service-name lookup table or Region catalog is embedded here.
    Classification comes from:
      1. Cost Explorer billing values,
      2. Resource Explorer inventory,
      3. references between discovered resource properties.

    "Primary" follows the caller's requested business definition: a service or
    Region with positive UnblendedCost in the current billing window.
    A discovered service with an actual Cost Explorer SERVICE record whose
    net amount is effectively zero is kept separately as
    ZERO_COST_OR_FREE_TIER_CANDIDATE. This is evidence of zero-cost billing,
    not proof that AWS Free Tier or a trial caused the zero charge.
    "Supporting" means a discovered service with no matched billing record and
    a data-derived resource relationship to a paid discovered service.
    """

    COST_EPSILON = 1e-9

    def classify(
        self,
        *,
        regions: AWSRegionDiscoveryResult,
        resources: AWSResourceDiscoveryResult,
        billing: AWSBillingDiscoveryResult,
    ) -> AWSInfrastructureClassificationResult:
        relationships = self._discover_relationships(resources.resources)
        service_result = self._classify_services(
            resources=resources,
            billing=billing,
            relationships=relationships,
        )
        region_result = self._classify_regions(
            regions=regions,
            resources=resources,
            billing=billing,
        )

        warnings = list(billing.warnings)
        if billing.available and not billing.service_costs:
            warnings.append(
                "Cost Explorer was reachable but returned no SERVICE cost groups "
                "for the selected billing window."
            )

        return AWSInfrastructureClassificationResult(
            billing_available=billing.available,
            primary_paid_services=service_result["primary"],
            zero_cost_services=service_result["zero_cost"],
            supporting_services=service_result["supporting"],
            discovered_unbilled_services=service_result["unbilled"],
            billing_only_services=service_result["billing_only"],
            non_positive_billing_services=service_result["non_positive"],
            paid_regions=region_result["paid"],
            used_unbilled_regions=region_result["used_unbilled"],
            enabled_unused_regions=region_result["enabled_unused"],
            billed_only_regions=region_result["billed_only"],
            relationships=relationships,
            warnings=warnings,
        )

    def _classify_services(
        self,
        *,
        resources: AWSResourceDiscoveryResult,
        billing: AWSBillingDiscoveryResult,
        relationships: list[AWSResourceRelationship],
    ) -> dict[str, list[AWSClassifiedService]]:
        discovered = {
            item.service.strip().lower(): item
            for item in resources.detected_services
            if item.service.strip()
        }

        # billing service -> best dynamically inferred discovered service
        billing_matches: dict[str, tuple[str, str, float] | None] = {}
        for cost in billing.service_costs:
            billing_matches[cost.billing_service] = self._best_service_match(
                billing_name=cost.billing_service,
                discovered_services=discovered.keys(),
            )

        matched_costs: dict[str, list[Any]] = defaultdict(list)
        unmatched_costs: list[Any] = []

        for cost in billing.service_costs:
            match = billing_matches.get(cost.billing_service)
            if match is None:
                unmatched_costs.append(cost)
                continue
            matched_costs[match[0]].append(cost)

        components_by_billing: dict[str, list[AWSBillingComponent]] = defaultdict(list)
        for component in billing.components:
            components_by_billing[component.billing_service].append(component)

        paid_discovered: set[str] = set()
        discovered_amounts: dict[str, float] = {}

        for service, costs in matched_costs.items():
            amount = sum(item.amount for item in costs)
            discovered_amounts[service] = amount
            if amount > self.COST_EPSILON:
                paid_discovered.add(service)

        adjacency: dict[str, set[str]] = defaultdict(set)
        for edge in relationships:
            left = (edge.source_service or "").strip().lower()
            right = (edge.target_service or "").strip().lower()
            if not left or not right or left == right:
                continue
            adjacency[left].add(right)
            adjacency[right].add(left)

        primary: list[AWSClassifiedService] = []
        zero_cost: list[AWSClassifiedService] = []
        supporting: list[AWSClassifiedService] = []
        unbilled: list[AWSClassifiedService] = []
        billing_only: list[AWSClassifiedService] = []
        non_positive: list[AWSClassifiedService] = []

        for service, discovered_entry in discovered.items():
            costs = matched_costs.get(service, [])
            amount = sum(item.amount for item in costs)
            billing_names = sorted({item.billing_service for item in costs})
            components = self._components_for_names(
                billing_names,
                components_by_billing,
            )

            match_methods = []
            match_confidences = []
            for name in billing_names:
                match = billing_matches.get(name)
                if match is not None:
                    match_methods.append(match[1])
                    match_confidences.append(match[2])

            related_primary = sorted(
                adjacent
                for adjacent in adjacency.get(service, set())
                if adjacent in paid_discovered
            )

            has_billing_record = bool(costs)

            if amount > self.COST_EPSILON:
                category = "PRIMARY_PAID"
                financial_status = "PAID"
            elif has_billing_record and abs(amount) <= self.COST_EPSILON:
                category = "ZERO_COST_OR_FREE_TIER_CANDIDATE"
                financial_status = "ZERO_COST_BILLING_EVIDENCE"
            elif has_billing_record and amount < -self.COST_EPSILON:
                category = "BILLING_CREDIT_OR_ADJUSTMENT"
                financial_status = "CREDIT_OR_ADJUSTMENT"
            elif related_primary:
                category = "SUPPORTING_RELATED"
                financial_status = "NO_BILLING_RECORD"
            else:
                category = "DISCOVERED_UNBILLED"
                financial_status = "NO_BILLING_RECORD"

            item = AWSClassifiedService(
                key=service,
                category=category,
                paid=amount > self.COST_EPSILON,
                financial_status=financial_status,
                billing_amount=amount,
                currency=billing.currency,
                billing_services=billing_names,
                billing_components=components,
                discovered_service=service,
                resource_count=discovered_entry.resource_count,
                regions=discovered_entry.regions,
                related_primary_services=related_primary,
                billing_match_method=(
                    ",".join(sorted(set(match_methods))) if match_methods else None
                ),
                billing_match_confidence=(
                    max(match_confidences) if match_confidences else None
                ),
            )

            if category == "PRIMARY_PAID":
                primary.append(item)
            elif category == "ZERO_COST_OR_FREE_TIER_CANDIDATE":
                zero_cost.append(item)
            elif category == "SUPPORTING_RELATED":
                supporting.append(item)
            elif category == "BILLING_CREDIT_OR_ADJUSTMENT":
                non_positive.append(item)
            else:
                unbilled.append(item)

        # Preserve unmatched Cost Explorer SERVICE entries as billing-only
        # evidence. They are not promoted to primary infrastructure services
        # because no discovered customer resource supports that conclusion.
        for cost in unmatched_costs:
            components = self._components_for_names(
                [cost.billing_service],
                components_by_billing,
            )
            is_positive = cost.amount > self.COST_EPSILON
            is_zero = abs(cost.amount) <= self.COST_EPSILON
            item = AWSClassifiedService(
                key=f"billing:{self._normalize(cost.billing_service)}",
                category=(
                    "PRIMARY_PAID_BILLING_ONLY"
                    if is_positive
                    else (
                        "ZERO_COST_BILLING_ONLY"
                        if is_zero
                        else "BILLING_CREDIT_OR_ADJUSTMENT_ONLY"
                    )
                ),
                paid=is_positive,
                financial_status=(
                    "PAID"
                    if is_positive
                    else (
                        "ZERO_COST_BILLING_EVIDENCE"
                        if is_zero
                        else "CREDIT_OR_ADJUSTMENT"
                    )
                ),
                billing_amount=cost.amount,
                currency=cost.unit or billing.currency,
                billing_services=[cost.billing_service],
                billing_components=components,
            )
            if item.paid:
                billing_only.append(item)
            else:
                non_positive.append(item)

        primary.sort(key=lambda item: (-item.billing_amount, item.key))
        zero_cost.sort(key=lambda item: (-item.resource_count, item.key))
        supporting.sort(key=lambda item: (-item.resource_count, item.key))
        unbilled.sort(key=lambda item: (-item.resource_count, item.key))
        billing_only.sort(key=lambda item: (-item.billing_amount, item.key))
        non_positive.sort(key=lambda item: (item.billing_amount, item.key))

        return {
            "primary": primary,
            "zero_cost": zero_cost,
            "supporting": supporting,
            "unbilled": unbilled,
            "billing_only": billing_only,
            "non_positive": non_positive,
        }

    def _classify_regions(
        self,
        *,
        regions: AWSRegionDiscoveryResult,
        resources: AWSResourceDiscoveryResult,
        billing: AWSBillingDiscoveryResult,
    ) -> dict[str, list[AWSClassifiedRegion]]:
        enabled = {
            item.region_name
            for item in regions.regions
            if item.enabled and item.region_name
        }

        resource_counts: dict[str, int] = defaultdict(int)
        for resource in resources.resources:
            region = (resource.region or "").strip()
            if region and region.lower() != "global":
                resource_counts[region] += 1

        billing_costs = {
            item.region: item
            for item in billing.region_costs
            if item.region
        }

        all_regions = sorted(
            enabled
            | set(resource_counts)
            | set(billing_costs)
        )

        result = {
            "paid": [],
            "used_unbilled": [],
            "enabled_unused": [],
            "billed_only": [],
        }

        for region in all_regions:
            billing_entry = billing_costs.get(region)
            amount = billing_entry.amount if billing_entry else 0.0
            unit = billing_entry.unit if billing_entry else billing.currency
            count = resource_counts.get(region, 0)
            is_enabled = region in enabled

            if amount > self.COST_EPSILON:
                category = (
                    "PAID_PRIMARY"
                    if is_enabled or count > 0
                    else "PAID_BILLING_ONLY"
                )
                bucket = "paid"
            elif count > 0:
                category = "USED_UNBILLED"
                bucket = "used_unbilled"
            elif is_enabled:
                category = "ENABLED_UNUSED"
                bucket = "enabled_unused"
            else:
                category = "BILLING_ONLY_NON_POSITIVE"
                bucket = "billed_only"

            result[bucket].append(
                AWSClassifiedRegion(
                    region=region,
                    category=category,
                    billing_amount=amount,
                    currency=unit,
                    resource_count=count,
                    enabled=is_enabled,
                )
            )

        result["paid"].sort(key=lambda item: (-item.billing_amount, item.region))
        result["used_unbilled"].sort(key=lambda item: (-item.resource_count, item.region))
        result["enabled_unused"].sort(key=lambda item: item.region)
        result["billed_only"].sort(key=lambda item: (item.billing_amount, item.region))
        return result

    @staticmethod
    def _components_for_names(
        billing_names: Iterable[str],
        components_by_billing: dict[str, list[AWSBillingComponent]],
    ) -> list[AWSBillingComponent]:
        components = [
            component
            for name in billing_names
            for component in components_by_billing.get(name, [])
        ]
        components.sort(key=lambda item: (-item.amount, item.usage_type))
        return components

    def _best_service_match(
        self,
        *,
        billing_name: str,
        discovered_services: Iterable[str],
    ) -> tuple[str, str, float] | None:
        billing_normalized = self._normalize(billing_name)
        aliases = self._dynamic_aliases(billing_name)

        best: tuple[str, str, float] | None = None

        for service in discovered_services:
            normalized = self._normalize(service)
            if not normalized:
                continue

            if normalized in aliases:
                candidate = (service, "dynamic_alias", 1.0)
            elif (
                len(normalized) >= 3
                and (
                    normalized in billing_normalized
                    or billing_normalized in normalized
                )
            ):
                candidate = (service, "normalized_substring", 0.92)
            else:
                ratio = SequenceMatcher(
                    None,
                    normalized,
                    billing_normalized,
                ).ratio()
                if ratio < 0.82:
                    continue
                candidate = (service, "string_similarity", round(ratio, 4))

            if best is None or candidate[2] > best[2]:
                best = candidate

        return best

    @classmethod
    def _dynamic_aliases(cls, value: str) -> set[str]:
        """
        Generate aliases from the billing name itself.

        Examples derived by the algorithm (not a lookup table):
          Elastic + Compute + Cloud -> e,c,c -> ec2
          Simple + Storage + Service -> s,s,s -> s3
          Relational + Database + Service -> rds
        """
        tokens = cls._words(value)
        aliases = {cls._normalize(value)}

        for token in tokens:
            aliases.add(cls._normalize(token))

        max_window = min(len(tokens), 7)
        for width in range(2, max_window + 1):
            for start in range(0, len(tokens) - width + 1):
                window = tokens[start : start + width]
                aliases.add(cls._normalize("".join(window)))
                aliases.add(cls._compress_initials(window))

        return {alias for alias in aliases if alias}

    @staticmethod
    def _words(value: str) -> list[str]:
        # Split camel-case, acronym boundaries, digit suffixes and punctuation.
        expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
        expanded = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", expanded)
        return re.findall(r"[A-Za-z]+\d*|\d+", expanded)

    @classmethod
    def _compress_initials(cls, words: list[str]) -> str:
        initials: list[str] = []
        for word in words:
            cleaned = cls._normalize(word)
            if cleaned:
                initials.append(cleaned[0])
        if not initials:
            return ""

        output: list[str] = []
        index = 0
        while index < len(initials):
            current = initials[index]
            end = index + 1
            while end < len(initials) and initials[end] == current:
                end += 1
            count = end - index
            output.append(current)
            if count > 1:
                output.append(str(count))
            index = end
        return "".join(output)

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    def _discover_relationships(
        self,
        resources: list[AWSResource],
    ) -> list[AWSResourceRelationship]:
        identifiers: dict[str, list[AWSResource]] = defaultdict(list)

        for resource in resources:
            for identifier in (resource.arn, resource.resource_id):
                normalized = (identifier or "").strip().lower()
                if len(normalized) >= 6:
                    identifiers[normalized].append(resource)

        relationships: list[AWSResourceRelationship] = []
        seen_pairs: set[tuple[str, str]] = set()

        for source in resources:
            source_key = self._resource_key(source)
            if not source_key:
                continue

            for scalar in self._flatten_scalars(source.properties):
                for candidate in self._reference_candidates(scalar):
                    for target in identifiers.get(candidate.lower(), []):
                        target_key = self._resource_key(target)
                        if not target_key or target_key == source_key:
                            continue

                        pair = tuple(sorted((source_key, target_key)))
                        if pair in seen_pairs:
                            continue
                        seen_pairs.add(pair)

                        relationships.append(
                            AWSResourceRelationship(
                                source_arn=source.arn,
                                source_resource_id=source.resource_id,
                                source_service=source.service,
                                target_arn=target.arn,
                                target_resource_id=target.resource_id,
                                target_service=target.service,
                                evidence=candidate,
                            )
                        )

        relationships.sort(
            key=lambda item: (
                item.source_service or "",
                item.source_resource_id or item.source_arn or "",
                item.target_service or "",
                item.target_resource_id or item.target_arn or "",
            )
        )
        return relationships

    @classmethod
    def _flatten_scalars(cls, value: Any) -> list[str]:
        output: list[str] = []
        if isinstance(value, dict):
            for child in value.values():
                output.extend(cls._flatten_scalars(child))
        elif isinstance(value, (list, tuple, set)):
            for child in value:
                output.extend(cls._flatten_scalars(child))
        elif value is not None:
            output.append(str(value))
        return output

    @staticmethod
    def _reference_candidates(value: str) -> set[str]:
        # Extract ARNs and resource-id-shaped tokens from arbitrary property
        # strings/JSON. No resource prefix catalog is required.
        matches = re.findall(
            r"arn:[^\s\"',}\]]+|[A-Za-z0-9][A-Za-z0-9._:/-]{5,}",
            value,
        )
        return {
            match.rstrip(".,;:)")
            for match in matches
            if len(match.rstrip(".,;:)")) >= 6
        }

    @staticmethod
    def _resource_key(resource: AWSResource) -> str | None:
        if resource.arn:
            return resource.arn.lower()
        if resource.resource_id:
            return (
                f"{(resource.service or '').lower()}|"
                f"{(resource.region or '').lower()}|"
                f"{resource.resource_id.lower()}"
            )
        return None
