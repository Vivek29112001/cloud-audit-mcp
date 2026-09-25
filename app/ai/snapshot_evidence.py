from __future__ import annotations
from datetime import date, datetime
from typing import Any
MAX_RESOURCE_EVIDENCE=20; MAX_SERVICE_EVIDENCE=35; MAX_REGION_EVIDENCE=25; MAX_ZONE_EVIDENCE=40; MAX_RELATIONSHIP_EVIDENCE=30; MAX_BILLING_COMPONENT_EVIDENCE=15; MAX_WARNING_EVIDENCE=20

def _norm(v): return str(v or "").strip().lower()
def _json_safe(v):
    if isinstance(v,(datetime,date)):return v.isoformat()
    if isinstance(v,dict):return {str(k):_json_safe(x) for k,x in v.items()}
    if isinstance(v,(list,tuple,set)):return [_json_safe(x) for x in v]
    return v

def _compact_json(v,depth=0,max_depth=5,max_items=50,max_string=1800):
    if depth>=max_depth:
        return "<nested data omitted>" if isinstance(v,(dict,list,tuple,set)) else v
    if isinstance(v,str):return v if len(v)<=max_string else v[:max_string]+"…<truncated>"
    if isinstance(v,dict):
        items=list(v.items()); out={str(k):_compact_json(x,depth+1,max_depth,max_items,max_string) for k,x in items[:max_items]}
        if len(items)>max_items:out["_truncated_fields"]=len(items)-max_items
        return out
    if isinstance(v,(list,tuple,set)):
        values=list(v); out=[_compact_json(x,depth+1,max_depth,max_items,max_string) for x in values[:max_items]]
        if len(values)>max_items:out.append({"_truncated_items":len(values)-max_items})
        return out
    return v

def _matches_service(item,service):
    if not service:return True
    target=_norm(service); candidates=[item.get("service"),item.get("service_namespace"),item.get("discovered_service"),item.get("key"),item.get("billing_service")]+list(item.get("billing_services") or [])
    return any(target==_norm(x) for x in candidates if x)
def _matches_resource(item,rid):
    if not rid:return True
    target=_norm(rid); return target in {_norm(item.get("resource_id")),_norm(item.get("arn"))}
def _compact_service(item):
    keys=("key","category","paid","financial_status","billing_amount","currency","billing_services","discovered_service","resource_count","regions","related_primary_services","billing_match_method","billing_match_confidence")
    return {k:item.get(k) for k in keys if item.get(k) is not None}
def _compact_resource(item,include_properties=False):
    out={k:item.get(k) for k in ("arn","resource_id","resource_type","service","region","owning_account_id") if item.get(k) is not None}
    if include_properties:
        props=item.get("properties") or []
        if isinstance(props,list):out["properties"]=props[:8]; out["properties_truncated"]=len(props)>8
    return out

def build_snapshot_evidence(*,scan_result:dict[str,Any],selected_context:dict[str,Any]|None,intent:dict[str,Any]|None)->dict[str,Any]:
    context=dict(selected_context or {}); intent=dict(intent or {})
    service=str(context.get("service") or context.get("service_namespace") or intent.get("service") or "").strip(); billing_service=str(context.get("billing_service") or "").strip(); target_service=service or billing_service
    rid=str(context.get("resource_id") or context.get("arn") or intent.get("resource_id") or "").strip(); region=str(context.get("region") or intent.get("region") or "").strip()
    rs=scan_result.get("resources") or {}; all_resources=[x for x in (rs.get("resources") or []) if isinstance(x,dict)]
    matches=[]
    for x in all_resources:
        if service and not _matches_service(x,service):continue
        if rid and not _matches_resource(x,rid):continue
        if region and _norm(x.get("region"))!=_norm(region):continue
        matches.append(x)
    raw=matches[:MAX_RESOURCE_EVIDENCE] if (service or rid or region) else all_resources[:5]
    resources=[_compact_resource(x,include_properties=bool(rid)) for x in raw]
    detected=[x for x in (rs.get("detected_services") or []) if isinstance(x,dict)][:MAX_SERVICE_EVIDENCE]
    cls=scan_result.get("classification") or {}; cls_view={"billing_available":cls.get("billing_available")}
    for bucket in ("primary_paid_services","zero_cost_services","supporting_services","discovered_unbilled_services","billing_only_services","non_positive_billing_services"):
        rows=[x for x in (cls.get(bucket) or []) if isinstance(x,dict)]
        if target_service: rows=[x for x in rows if _matches_service(x,target_service)]
        cls_view[bucket]=[_compact_service(x) for x in rows[:MAX_SERVICE_EVIDENCE]]; cls_view[bucket+"_truncated"]=len(rows)>MAX_SERVICE_EVIDENCE
    for bucket in ("paid_regions","used_unbilled_regions","enabled_unused_regions","billed_only_regions"):
        rows=[x for x in (cls.get(bucket) or []) if isinstance(x,dict)]
        if region:rows=[x for x in rows if _norm(x.get("region"))==_norm(region)]
        cls_view[bucket]=rows[:MAX_REGION_EVIDENCE]
    relationships=[x for x in (cls.get("relationships") or []) if isinstance(x,dict)]
    if service or rid:
        relationships=[x for x in relationships if (_norm(service) and _norm(service) in {_norm(x.get("source_service")),_norm(x.get("target_service"))}) or (_norm(rid) and _norm(rid) in {_norm(x.get("source_resource_id")),_norm(x.get("source_arn")),_norm(x.get("target_resource_id")),_norm(x.get("target_arn"))})]
    else:relationships=relationships[:5]
    cls_view["relationships"]=relationships[:MAX_RELATIONSHIP_EVIDENCE]
    billing=scan_result.get("billing") or {}; service_costs=[x for x in (billing.get("service_costs") or []) if isinstance(x,dict)]
    if billing_service:service_costs=[x for x in service_costs if _norm(x.get("billing_service"))==_norm(billing_service)]
    region_costs=[x for x in (billing.get("region_costs") or []) if isinstance(x,dict)]
    if region:region_costs=[x for x in region_costs if _norm(x.get("region"))==_norm(region)]
    components=[]
    if target_service:
        rawc=[x for x in (billing.get("components") or []) if isinstance(x,dict)]
        if billing_service:rawc=[x for x in rawc if _norm(x.get("billing_service"))==_norm(billing_service)]
        components=rawc[:MAX_BILLING_COMPONENT_EVIDENCE]
    regions_data=scan_result.get("regions") or {}; region_rows=[x for x in (regions_data.get("regions") or []) if isinstance(x,dict)]
    if region:region_rows=[x for x in region_rows if _norm(x.get("region_name"))==_norm(region)]
    zones_data=scan_result.get("zones") or {}; zone_rows=[x for x in (zones_data.get("zones") or []) if isinstance(x,dict)]
    if region:zone_rows=[x for x in zone_rows if _norm(x.get("region_name"))==_norm(region)]
    evidence={"evidence_source":"PERSISTED_DISCOVERY_SNAPSHOT","scan_id":scan_result.get("scan_id"),"scan_status":scan_result.get("status"),"scan_started_at":scan_result.get("started_at"),"scan_completed_at":scan_result.get("completed_at"),"selected_context":context,"account":scan_result.get("account") or {},"summary":scan_result.get("summary") or {},"regions":{"total_regions":regions_data.get("total_regions"),"enabled_regions":regions_data.get("enabled_regions"),"disabled_regions":regions_data.get("disabled_regions"),"regions":region_rows[:MAX_REGION_EVIDENCE]},"zones":{"total_zones":zones_data.get("total_zones"),"zones":zone_rows[:MAX_ZONE_EVIDENCE]},"resources":{"total_resources":rs.get("total_resources",0),"used_regions":rs.get("used_regions") or [],"detected_services":detected,"matching_resources":resources,"matching_resource_count":len(matches) if (service or rid or region) else len(all_resources),"resource_evidence_truncated":len(matches)>len(raw) if (service or rid or region) else len(all_resources)>len(raw)},"billing":{"available":billing.get("available"),"period_start":billing.get("period_start"),"period_end_exclusive":billing.get("period_end_exclusive"),"metric":billing.get("metric"),"currency":billing.get("currency"),"total_cost":billing.get("total_cost"),"service_costs":service_costs[:MAX_SERVICE_EVIDENCE],"region_costs":region_costs[:MAX_REGION_EVIDENCE],"components":components,"warnings":(billing.get("warnings") or [])[:MAX_WARNING_EVIDENCE]},"classification":cls_view,"scan_warnings":(scan_result.get("warnings") or [])[:MAX_WARNING_EVIDENCE]}
    return _compact_json(_json_safe(evidence))
