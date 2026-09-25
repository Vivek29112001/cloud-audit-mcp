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
    COST_EPSILON = 1e-9

    def classify(self, *, regions: AWSRegionDiscoveryResult, resources: AWSResourceDiscoveryResult, billing: AWSBillingDiscoveryResult) -> AWSInfrastructureClassificationResult:
        relationships = self._discover_relationships(resources.resources)
        service_result = self._classify_services(resources=resources, billing=billing, relationships=relationships)
        region_result = self._classify_regions(regions=regions, resources=resources, billing=billing)
        warnings = list(billing.warnings)
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

    def _classify_services(self, *, resources: AWSResourceDiscoveryResult, billing: AWSBillingDiscoveryResult, relationships: list[AWSResourceRelationship]):
        discovered = {x.service.strip().lower(): x for x in resources.detected_services if x.service.strip()}
        billing_matches = {x.billing_service: self._best_service_match(billing_name=x.billing_service, discovered_services=discovered.keys()) for x in billing.service_costs}
        matched = defaultdict(list); unmatched=[]
        for cost in billing.service_costs:
            match=billing_matches.get(cost.billing_service)
            (matched[match[0]] if match else unmatched).append(cost)
        components_by_billing=defaultdict(list)
        for c in billing.components: components_by_billing[c.billing_service].append(c)

        paid_discovered=set()
        for service,costs in matched.items():
            if sum(x.amount for x in costs)>self.COST_EPSILON: paid_discovered.add(service)

        adjacency=defaultdict(set)
        for edge in relationships:
            a=(edge.source_service or "").lower().strip(); b=(edge.target_service or "").lower().strip()
            if a and b and a!=b: adjacency[a].add(b); adjacency[b].add(a)

        primary=[]; zero_cost=[]; supporting=[]; unbilled=[]; billing_only=[]; non_positive=[]
        for service, entry in discovered.items():
            costs=matched.get(service,[]); amount=sum(x.amount for x in costs)
            names=sorted({x.billing_service for x in costs})
            comps=self._components_for_names(names,components_by_billing)
            methods=[]; confidences=[]
            for name in names:
                m=billing_matches.get(name)
                if m: methods.append(m[1]); confidences.append(m[2])
            related=sorted(x for x in adjacency.get(service,set()) if x in paid_discovered)
            has_billing=bool(costs)
            if amount>self.COST_EPSILON:
                category="PRIMARY_PAID"; financial="PAID"
            elif has_billing and abs(amount)<=self.COST_EPSILON:
                category="ZERO_COST_OR_FREE_TIER_CANDIDATE"; financial="ZERO_COST_BILLING_EVIDENCE"
            elif has_billing and amount < -self.COST_EPSILON:
                category="BILLING_CREDIT_OR_ADJUSTMENT"; financial="CREDIT_OR_ADJUSTMENT"
            elif related:
                category="SUPPORTING_RELATED"; financial="NO_BILLING_RECORD"
            else:
                category="DISCOVERED_UNBILLED"; financial="NO_BILLING_RECORD"
            item=AWSClassifiedService(key=service,category=category,paid=amount>self.COST_EPSILON,financial_status=financial,billing_amount=amount,currency=billing.currency,billing_services=names,billing_components=comps,discovered_service=service,resource_count=entry.resource_count,regions=entry.regions,related_primary_services=related,billing_match_method=(",".join(sorted(set(methods))) if methods else None),billing_match_confidence=(max(confidences) if confidences else None))
            if category=="PRIMARY_PAID": primary.append(item)
            elif category=="ZERO_COST_OR_FREE_TIER_CANDIDATE": zero_cost.append(item)
            elif category=="SUPPORTING_RELATED": supporting.append(item)
            elif category=="BILLING_CREDIT_OR_ADJUSTMENT": non_positive.append(item)
            else: unbilled.append(item)

        for cost in unmatched:
            positive=cost.amount>self.COST_EPSILON; zero=abs(cost.amount)<=self.COST_EPSILON
            item=AWSClassifiedService(
                key=f"billing:{self._normalize(cost.billing_service)}",
                category=("PRIMARY_PAID_BILLING_ONLY" if positive else ("ZERO_COST_BILLING_ONLY" if zero else "BILLING_CREDIT_OR_ADJUSTMENT_ONLY")),
                paid=positive,
                financial_status=("PAID" if positive else ("ZERO_COST_BILLING_EVIDENCE" if zero else "CREDIT_OR_ADJUSTMENT")),
                billing_amount=cost.amount,
                currency=cost.unit or billing.currency,
                billing_services=[cost.billing_service],
                billing_components=self._components_for_names([cost.billing_service],components_by_billing),
            )
            (billing_only if positive else non_positive).append(item)

        primary.sort(key=lambda x:(-x.billing_amount,x.key)); zero_cost.sort(key=lambda x:(-x.resource_count,x.key)); supporting.sort(key=lambda x:(-x.resource_count,x.key)); unbilled.sort(key=lambda x:(-x.resource_count,x.key)); billing_only.sort(key=lambda x:(-x.billing_amount,x.key)); non_positive.sort(key=lambda x:(x.billing_amount,x.key))
        return {"primary":primary,"zero_cost":zero_cost,"supporting":supporting,"unbilled":unbilled,"billing_only":billing_only,"non_positive":non_positive}

    def _classify_regions(self, *, regions, resources, billing):
        enabled={x.region_name for x in regions.regions if x.enabled and x.region_name}; counts=defaultdict(int)
        for r in resources.resources:
            region=(r.region or "").strip()
            if region and region.lower()!="global": counts[region]+=1
        costs={x.region:x for x in billing.region_costs if x.region}; result={"paid":[],"used_unbilled":[],"enabled_unused":[],"billed_only":[]}
        for region in sorted(enabled|set(counts)|set(costs)):
            ce=costs.get(region); amount=ce.amount if ce else 0.0; unit=ce.unit if ce else billing.currency; count=counts.get(region,0); en=region in enabled
            if amount>self.COST_EPSILON: category="PAID_PRIMARY" if en or count else "PAID_BILLING_ONLY"; bucket="paid"
            elif count: category="USED_UNBILLED"; bucket="used_unbilled"
            elif en: category="ENABLED_UNUSED"; bucket="enabled_unused"
            else: category="BILLING_ONLY_NON_POSITIVE"; bucket="billed_only"
            result[bucket].append(AWSClassifiedRegion(region=region,category=category,billing_amount=amount,currency=unit,resource_count=count,enabled=en))
        for k in result: result[k].sort(key=lambda x:x.region)
        result["paid"].sort(key=lambda x:(-x.billing_amount,x.region))
        return result

    @staticmethod
    def _components_for_names(names: Iterable[str], mapping):
        out=[c for n in names for c in mapping.get(n,[])]; out.sort(key=lambda x:(-x.amount,x.usage_type)); return out

    def _best_service_match(self, *, billing_name: str, discovered_services: Iterable[str]):
        billing_norm=self._normalize(billing_name); aliases=self._dynamic_aliases(billing_name); best=None
        for service in discovered_services:
            norm=self._normalize(service)
            if not norm: continue
            if norm in aliases: cand=(service,"dynamic_alias",1.0)
            elif len(norm)>=3 and (norm in billing_norm or billing_norm in norm): cand=(service,"normalized_substring",0.92)
            else:
                ratio=SequenceMatcher(None,norm,billing_norm).ratio()
                if ratio<0.82: continue
                cand=(service,"string_similarity",round(ratio,4))
            if best is None or cand[2]>best[2]: best=cand
        return best

    @classmethod
    def _dynamic_aliases(cls,value):
        tokens=cls._words(value); aliases={cls._normalize(value)}
        for t in tokens: aliases.add(cls._normalize(t))
        for width in range(2,min(len(tokens),7)+1):
            for start in range(0,len(tokens)-width+1):
                window=tokens[start:start+width]; aliases.add(cls._normalize("".join(window))); aliases.add(cls._compress_initials(window))
        return {x for x in aliases if x}
    @staticmethod
    def _words(value):
        expanded=re.sub(r"([a-z0-9])([A-Z])",r"\1 \2",value); expanded=re.sub(r"([A-Z]+)([A-Z][a-z])",r"\1 \2",expanded); return re.findall(r"[A-Za-z]+\d*|\d+",expanded)
    @classmethod
    def _compress_initials(cls,words):
        initials=[cls._normalize(w)[0] for w in words if cls._normalize(w)]; out=[]; i=0
        while i<len(initials):
            c=initials[i]; j=i+1
            while j<len(initials) and initials[j]==c:j+=1
            out.append(c); count=j-i
            if count>1:out.append(str(count))
            i=j
        return "".join(out)
    @staticmethod
    def _normalize(value): return re.sub(r"[^a-z0-9]+","",value.lower())

    def _discover_relationships(self, resources: list[AWSResource]):
        ids=defaultdict(list)
        for r in resources:
            for identifier in (r.arn,r.resource_id):
                n=(identifier or "").strip().lower()
                if len(n)>=6: ids[n].append(r)
        out=[]; seen=set()
        for source in resources:
            sk=self._resource_key(source)
            if not sk:continue
            for scalar in self._flatten_scalars(source.properties):
                for candidate in self._reference_candidates(scalar):
                    for target in ids.get(candidate.lower(),[]):
                        tk=self._resource_key(target)
                        if not tk or tk==sk:continue
                        pair=tuple(sorted((sk,tk)))
                        if pair in seen:continue
                        seen.add(pair); out.append(AWSResourceRelationship(source_arn=source.arn,source_resource_id=source.resource_id,source_service=source.service,target_arn=target.arn,target_resource_id=target.resource_id,target_service=target.service,evidence=candidate))
        return out
    @classmethod
    def _flatten_scalars(cls,v):
        out=[]
        if isinstance(v,dict):
            for c in v.values():out.extend(cls._flatten_scalars(c))
        elif isinstance(v,(list,tuple,set)):
            for c in v:out.extend(cls._flatten_scalars(c))
        elif v is not None:out.append(str(v))
        return out
    @staticmethod
    def _reference_candidates(v): return {m.rstrip(".,;:)") for m in re.findall(r"arn:[^\s\"',}\]]+|[A-Za-z0-9][A-Za-z0-9._:/-]{5,}",v) if len(m.rstrip(".,;:)"))>=6}
    @staticmethod
    def _resource_key(r):
        if r.arn:return r.arn.lower()
        if r.resource_id:return f"{(r.service or '').lower()}|{(r.region or '').lower()}|{r.resource_id.lower()}"
        return None
