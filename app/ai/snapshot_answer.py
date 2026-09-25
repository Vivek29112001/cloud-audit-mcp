from __future__ import annotations
from typing import Any

def _norm(v):return str(v or "").strip().lower()
def _unique(values):
    seen=set();out=[]
    for v in values:
        t=str(v or "").strip();k=t.lower()
        if t and k not in seen:seen.add(k);out.append(t)
    return out
def _label(e):
    c=e.get("selected_context") or {};return str(c.get("label") or c.get("billing_service") or c.get("service") or c.get("resource_id") or c.get("region") or "the selected AWS context")
def _service_rows(e):
    c=e.get("classification") or {};rows=[]
    for b in ("primary_paid_services","zero_cost_services","supporting_services","discovered_unbilled_services","billing_only_services","non_positive_billing_services"):
        rows.extend(x for x in (c.get(b) or []) if isinstance(x,dict))
    return rows

def try_generate_snapshot_answer(*,question:str,snapshot_evidence:dict[str,Any])->str|None:
    q=_norm(question);e=snapshot_evidence;label=_label(e);ctx=e.get("selected_context") or {};when=e.get("scan_completed_at") or e.get("scan_started_at");suffix=f" in the saved scan from {when}" if when else " in the saved scan"
    if "region" in q:
        vals=list(ctx.get("regions") or [])
        for x in (e.get("resources") or {}).get("matching_resources") or []:
            if isinstance(x,dict):vals.append(x.get("region"))
        for x in _service_rows(e):vals.extend(x.get("regions") or [])
        if ctx.get("region"):vals.append(ctx.get("region"))
        regions=_unique(vals)
        return (f"{label} was associated with {len(regions)} AWS Region{'s' if len(regions)!=1 else ''}{suffix}: "+", ".join(regions)+".") if regions else f"The saved snapshot does not contain Region evidence for {label}."
    if "resource" in q:
        r=e.get("resources") or {};rows=[x for x in (r.get("matching_resources") or []) if isinstance(x,dict)];total=r.get("matching_resource_count")
        if rows:
            ids=_unique([x.get("resource_id") or x.get("arn") or x.get("resource_type") for x in rows]);return f"{label} has {total if total is not None else len(rows)} matching resource(s){suffix}."+(" Resources shown: "+", ".join(ids)+"." if ids else "")
        if total==0:return f"No matching resources for {label} were recorded{suffix}."
    if any(t in q for t in ("cost","billing","bill","spend","price")):
        b=e.get("billing") or {};costs=[x for x in (b.get("service_costs") or []) if isinstance(x,dict)];target=_norm(ctx.get("billing_service"))
        if target:costs=[x for x in costs if _norm(x.get("billing_service"))==target]
        if costs:
            return "Saved-snapshot billing evidence: "+"; ".join(f"{x.get('billing_service') or label}: {x.get('amount') if x.get('amount') is not None else x.get('cost')} {x.get('unit') or x.get('currency') or b.get('currency') or ''}".strip() for x in costs[:10])+"."
    if "service" in q and any(t in q for t in ("list","show","which","what")):
        names=_unique([x.get("service") if isinstance(x,dict) else x for x in ((e.get("resources") or {}).get("detected_services") or [])]);
        if names:return f"The saved scan contains {len(names)} resource-backed AWS service(s): "+", ".join(names)+"."
    return None
