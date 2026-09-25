from __future__ import annotations
import json
from groq import Groq
from app.ai.intent_models import AWSQueryIntent
from app.core.config import settings

class GroqIntentClient:
    def __init__(self):
        if not settings.groq_api_key: raise RuntimeError("GROQ_API_KEY is not configured.")
        self._client=Groq(api_key=settings.groq_api_key)

    def parse_aws_question(self, question:str, conversation_context:str|None=None, selected_context:dict|None=None)->AWSQueryIntent:
        question=(question or "").strip()
        if not question: raise ValueError("AWS question cannot be empty.")
        schema={"type":"object","properties":{"service":{"type":"string"},"operation":{"type":"string"},"region":{"type":["string","null"]},"params_json":{"type":"string"},"resource_id":{"type":["string","null"]}},"required":["service","operation","region","params_json","resource_id"],"additionalProperties":False}
        system_prompt=r'''
You are the query planner for a read-only AWS audit application.
There are two evidence paths: a saved immutable discovery snapshot and live read-only AWS.
Use operation exactly SnapshotLookup when the saved snapshot should answer the question.
Use operation exactly OutOfScope when the request is unrelated to AWS/cloud-audit context.
Use one REAL read-only AWS API operation only when current/live state or configuration not stored in the baseline snapshot is required.

Snapshot evidence can include account identity, Regions, Availability Zones, discovered services/resources, billing/cost, classifications, and resource relationships.
Default to SnapshotLookup for questions about what was discovered, service/resource/Region lists, saved costs, classifications, or follow-ups about a selected Discovery item.
Use live AWS for explicit current/right-now/latest state or configuration/details absent from baseline discovery.
For SnapshotLookup params_json MUST be exactly "{}".
For live calls use only safe read operation families: Get*, List*, Describe*, Search*, Lookup*, BatchGet*, Select*.
Never choose Create*, Delete*, Put*, Update*, Modify*, Terminate*, Start*, Stop*, Run*, Invoke*, Attach*, Detach*, Enable*, Disable*, Register*, Deregister*, Set*, Tag*, Untag*.
Never invent resources, identifiers, Regions or operations.
For unrelated requests (for example sports, general coding, writing, non-AWS trivia), return service="", operation="OutOfScope", region=null, params_json="{}", resource_id=null.
If there is a structured AWS selection, a natural follow-up such as "what about its region?" remains in scope.
Structured selected context identifies the saved item the user clicked and may resolve words such as this/it/that resource.
Conversation context is for reference resolution only.
'''
        context=(conversation_context or "").strip()[-6000:]
        prompt=f"Structured discovery selection:\n{json.dumps(selected_context or {},default=str)}\n\nRecent conversation context:\n{context}\n\nCurrent user question:\n{question}"
        response=self._client.chat.completions.create(model=settings.groq_intent_model,temperature=0,messages=[{"role":"system","content":system_prompt},{"role":"user","content":prompt}],response_format={"type":"json_schema","json_schema":{"name":"aws_query_intent","strict":True,"schema":schema}})
        content=response.choices[0].message.content
        if not content: raise RuntimeError("Groq returned an empty intent response.")
        try:data=json.loads(content)
        except json.JSONDecodeError as exc: raise RuntimeError("Groq returned invalid JSON for AWS intent.") from exc
        data["requires_live_data"] = str(data.get("operation") or "").strip().lower() != "snapshotlookup"
        return AWSQueryIntent(**data)
