from __future__ import annotations
import json
from typing import Any
from groq import Groq
from app.core.config import settings

class GroqAnswerGenerator:
    def __init__(self):
        if not settings.groq_api_key: raise RuntimeError("GROQ_API_KEY is not configured.")
        self._client=Groq(api_key=settings.groq_api_key)

    def generate(self, *, question:str, intent:dict[str,Any], aws_result:dict[str,Any])->str:
        system_prompt='''You format read-only AWS audit evidence. Answer only from supplied AWS evidence. Never invent resources, Regions, counts or security findings. Mention partial coverage. Keep concise and audit-friendly. Never expose credentials or tokens.'''
        payload={"question":question,"intent":intent,"aws_result":aws_result}
        response=self._client.chat.completions.create(model=settings.groq_intent_model,temperature=0,max_tokens=700,messages=[{"role":"system","content":system_prompt},{"role":"user","content":json.dumps(payload,default=str)}])
        return response.choices[0].message.content or "The AWS query completed, but no formatted answer was generated."

    @staticmethod
    def _bounded_snapshot_payload(*,question:str,snapshot_evidence:dict[str,Any],conversation_context:str|None,max_chars:int=14000)->str:
        payload={"question":question,"conversation_context":(conversation_context or "")[-1500:],"snapshot_evidence":snapshot_evidence}
        encoded=json.dumps(payload,default=str,separators=(",",":"))
        if len(encoded)<=max_chars:return encoded
        e=snapshot_evidence;r=e.get("resources") or {};b=e.get("billing") or {};c=e.get("classification") or {};regions=e.get("regions") or {}
        compact_c={"billing_available":c.get("billing_available")}
        for k in ("primary_paid_services","zero_cost_services","supporting_services","discovered_unbilled_services","billing_only_services","non_positive_billing_services"):compact_c[k]=(c.get(k) or [])[:6]
        for k in ("paid_regions","used_unbilled_regions","enabled_unused_regions","billed_only_regions"):compact_c[k]=(c.get(k) or [])[:12]
        compact_c["relationships"]=(c.get("relationships") or [])[:8]
        compact={"evidence_source":e.get("evidence_source"),"scan_id":e.get("scan_id"),"scan_completed_at":e.get("scan_completed_at"),"selected_context":e.get("selected_context") or {},"account":e.get("account") or {},"summary":e.get("summary") or {},"resources":{"total_resources":r.get("total_resources"),"used_regions":(r.get("used_regions") or [])[:15],"detected_services":(r.get("detected_services") or [])[:12],"matching_resources":(r.get("matching_resources") or [])[:8],"matching_resource_count":r.get("matching_resource_count")},"billing":{"available":b.get("available"),"period_start":b.get("period_start"),"period_end_exclusive":b.get("period_end_exclusive"),"currency":b.get("currency"),"total_cost":b.get("total_cost"),"service_costs":(b.get("service_costs") or [])[:10],"region_costs":(b.get("region_costs") or [])[:10],"components":(b.get("components") or [])[:4]},"classification":compact_c,"regions":{"total_regions":regions.get("total_regions"),"enabled_regions":regions.get("enabled_regions"),"disabled_regions":regions.get("disabled_regions"),"regions":(regions.get("regions") or [])[:12]}}
        payload["snapshot_evidence"]=compact; encoded=json.dumps(payload,default=str,separators=(",",":"))
        if len(encoded)<=max_chars:return encoded
        minimal={"question":question[:1000],"snapshot_evidence":{"evidence_source":e.get("evidence_source"),"scan_id":e.get("scan_id"),"scan_completed_at":e.get("scan_completed_at"),"selected_context":e.get("selected_context") or {},"summary":e.get("summary") or {},"matching_resource_count":r.get("matching_resource_count"),"matching_resources":(r.get("matching_resources") or [])[:2]}}
        return json.dumps(minimal,default=str,separators=(",",":"))

    def generate_snapshot(self,*,question:str,snapshot_evidence:dict[str,Any],conversation_context:str|None=None)->str:
        system_prompt='''You format answers from a SAVED IMMUTABLE AWS discovery snapshot. Answer only from supplied snapshot evidence. Frame facts as true at scan time. If evidence is insufficient, say what is missing and that a live read-only query may be needed. Use selected context for references. Never invent resources, Regions, costs, relationships, or current state.'''
        user_payload=self._bounded_snapshot_payload(question=question,snapshot_evidence=snapshot_evidence,conversation_context=conversation_context)
        response=self._client.chat.completions.create(model=settings.groq_intent_model,temperature=0,max_tokens=700,messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_payload}])
        return response.choices[0].message.content or "The saved AWS snapshot contains no formatted answer for this question."
