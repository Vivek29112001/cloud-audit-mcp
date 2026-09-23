# from __future__ import annotations

# import json

# from groq import Groq

# from app.ai.intent_models import (
#     AWSQueryIntent,
# )

# from app.core.config import (
#     settings,
# )


# class GroqIntentClient:

#     def __init__(self) -> None:

#         if not settings.groq_api_key:
#             raise RuntimeError(
#                 "GROQ_API_KEY is not configured."
#             )

#         self._client = Groq(
#             api_key=(
#                 settings.groq_api_key
#             )
#         )

#     def parse_aws_question(
#         self,
#         question: str,
#         conversation_context: str | None = None,
#     ) -> AWSQueryIntent:
#         """
#         Convert a natural-language AWS question
#         into ONE safe read-only AWS API operation.

#         Recent conversation context may be supplied
#         only to resolve references such as:

#         - those
#         - them
#         - it
#         - that instance
#         - those databases

#         The returned plan is still validated by the
#         backend read-only validator before AWS MCP
#         execution.
#         """

#         question = (
#             question
#             or ""
#         ).strip()

#         if not question:
#             raise ValueError(
#                 "AWS question cannot be empty."
#             )

#         schema = {
#             "type": "object",

#             "properties": {

#                 "service": {
#                     "type": "string",
#                 },

#                 "operation": {
#                     "type": "string",
#                 },

#                 "region": {
#                     "type": [
#                         "string",
#                         "null",
#                     ],
#                 },

#                 "params_json": {
#                     "type": "string",
#                 },

#                 "resource_id": {
#                     "type": [
#                         "string",
#                         "null",
#                     ],
#                 },

#                 "requires_live_data": {
#                     "type": "boolean",
#                 },
#             },

#             "required": [
#                 "service",
#                 "operation",
#                 "region",
#                 "params_json",
#                 "resource_id",
#                 "requires_live_data",
#             ],

#             "additionalProperties": False,
#         }

#         system_prompt = r'''
# You are the query planner for a read-only AWS infrastructure
# auditing application.

# Your job is ONLY to convert the user's question into one real
# AWS read API operation.

# Do not answer the infrastructure question yourself.

# Return these fields:

# - service:
#   AWS SDK service identifier, for example:
#   ec2, rds, lambda, dynamodb, iam, s3, eks, ecs,
#   cloudtrail, kms.

# - operation:
#   one REAL AWS API operation in PascalCase.

# - region:
#   only when the user explicitly specifies a Region;
#   otherwise null.

# - params_json:
#   a STRING containing a valid JSON object representing
#   AWS API parameters.

# - resource_id:
#   a resource identifier only when the user explicitly
#   provides one or when recent conversation context makes
#   the reference unambiguous.
#   Otherwise null.

# - requires_live_data:
#   normally true for AWS account/infrastructure questions.


# CRITICAL SAFETY RULES:

# 1. Never invent AWS API operation names.

# 2. Only choose read-only operations such as:
#    Get*
#    List*
#    Describe*
#    Search*
#    Lookup*
#    BatchGet*
#    Select*

# 3. Never choose write/change operations such as:
#    Create*
#    Delete*
#    Put*
#    Update*
#    Modify*
#    Terminate*
#    Start*
#    Stop*
#    Run*
#    Invoke*
#    Attach*
#    Detach*
#    Enable*
#    Disable*
#    Register*
#    Deregister*
#    Set*
#    Tag*
#    Untag*

# 4. params_json MUST always be a JSON STRING.

# 5. When no parameters are required, return exactly:
#    "{}"

# 6. Never invent Regions.

# 7. Never invent resource IDs.

# 8. If the question needs several AWS API operations,
#    choose the PRIMARY read operation only.
#    A later complex-query workflow will handle multi-call
#    correlation.

# 9. Recent conversation may be supplied only to resolve
#    conversational references such as:
#    "those"
#    "them"
#    "these"
#    "it"
#    "that instance"
#    "those databases"
#    "the previous resources"

# 10. Previous assistant responses are CONTEXT ONLY.
#     They are not authoritative current AWS state.

# 11. Infrastructure questions must still be answered using
#     a live read-only AWS operation when
#     requires_live_data=true.

# 12. Do not reuse stale infrastructure information merely
#     because it appeared in conversation history.

# 13. Conversation context must never cause you to invent:
#     - AWS services
#     - Regions
#     - resources
#     - resource identifiers
#     - operations


# CORRECT EXAMPLES:


# User:
# show all ec2 instances

# service = ec2
# operation = DescribeInstances
# region = null
# params_json = "{}"
# resource_id = null
# requires_live_data = true


# User:
# show my VPCs

# service = ec2
# operation = DescribeVpcs
# region = null
# params_json = "{}"
# resource_id = null
# requires_live_data = true


# User:
# show rds databases

# service = rds
# operation = DescribeDBInstances
# region = null
# params_json = "{}"
# resource_id = null
# requires_live_data = true


# User:
# show lambda functions

# service = lambda
# operation = ListFunctions
# region = null
# params_json = "{}"
# resource_id = null
# requires_live_data = true


# User:
# show dynamodb tables

# service = dynamodb
# operation = ListTables
# region = null
# params_json = "{}"
# resource_id = null
# requires_live_data = true


# User:
# show IAM users

# service = iam
# operation = ListUsers
# region = null
# params_json = "{}"
# resource_id = null
# requires_live_data = true


# User:
# show EKS clusters

# service = eks
# operation = ListClusters
# region = null
# params_json = "{}"
# resource_id = null
# requires_live_data = true


# User:
# show ECS clusters

# service = ecs
# operation = ListClusters
# region = null
# params_json = "{}"
# resource_id = null
# requires_live_data = true


# User:
# show instance i-1234567890

# service = ec2
# operation = DescribeInstances
# region = null
# params_json = "{\"InstanceIds\":[\"i-1234567890\"]}"
# resource_id = i-1234567890
# requires_live_data = true


# Conversation:

# User:
# show all EC2 instances

# Assistant:
# I found several EC2 instances.

# Current User:
# which of those are running?

# Expected planner direction:

# service = ec2
# operation = DescribeInstances
# region = null
# params_json = "{}"
# resource_id = null
# requires_live_data = true


# Conversation:

# User:
# show my RDS databases

# Assistant:
# The account contains multiple RDS databases.

# Current User:
# which of them are publicly accessible?

# Expected planner direction:

# service = rds
# operation = DescribeDBInstances
# region = null
# params_json = "{}"
# resource_id = null
# requires_live_data = true
# '''

#         context_text = (
#             conversation_context
#             or ""
#         ).strip()

#         if context_text:

#             user_prompt = f"""
# Recent conversation context:

# {context_text}


# Current user question:

# {question}


# Use recent conversation context only to resolve
# references in the current question.

# Do not treat previous assistant output as current AWS
# state.

# Always choose a live read-only AWS API operation when
# the current question requires AWS infrastructure data.
# """

#         else:

#             user_prompt = question

#         response = (
#             self._client
#             .chat.completions
#             .create(
#                 model=(
#                     settings
#                     .groq_intent_model
#                 ),

#                 temperature=0,

#                 messages=[
#                     {
#                         "role": "system",
#                         "content":
#                             system_prompt,
#                     },
#                     {
#                         "role": "user",
#                         "content":
#                             user_prompt,
#                     },
#                 ],

#                 response_format={
#                     "type":
#                         "json_schema",

#                     "json_schema": {
#                         "name":
#                             "aws_query_intent",

#                         "strict": True,

#                         "schema":
#                             schema,
#                     },
#                 },
#             )
#         )

#         content = (
#             response
#             .choices[0]
#             .message
#             .content
#         )

#         if not content:
#             raise RuntimeError(
#                 "Groq returned an empty "
#                 "intent response."
#             )

#         try:

#             data = json.loads(
#                 content
#             )

#         except json.JSONDecodeError as exc:

#             raise RuntimeError(
#                 "Groq returned invalid JSON "
#                 "for AWS intent."
#             ) from exc

#         return AWSQueryIntent(
#             **data
#         )



from __future__ import annotations

import json

from groq import Groq

from app.ai.intent_models import AWSQueryIntent
from app.core.config import settings


class GroqIntentClient:
    def __init__(self) -> None:
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")
        self._client = Groq(api_key=settings.groq_api_key)

    def parse_aws_question(
        self,
        question: str,
        conversation_context: str | None = None,
        selected_context: dict | None = None,
    ) -> AWSQueryIntent:
        """
        Decide whether the question can be answered from the persisted discovery
        snapshot or requires one safe live AWS read operation.
        """
        question = (question or "").strip()
        if not question:
            raise ValueError("AWS question cannot be empty.")

        schema = {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "operation": {"type": "string"},
                "region": {"type": ["string", "null"]},
                "params_json": {"type": "string"},
                "resource_id": {"type": ["string", "null"]},
            },
            "required": [
                "service",
                "operation",
                "region",
                "params_json",
                "resource_id",
            ],
            "additionalProperties": False,
        }

        system_prompt = r'''
You are the query planner for a read-only AWS audit application.

The application has TWO evidence paths:

A) SAVED DISCOVERY SNAPSHOT
The persisted snapshot can contain:
- AWS account identity
- enabled/disabled Regions
- Availability Zones
- discovered AWS services
- discovered AWS resources and ARNs/resource IDs
- used Regions
- Cost Explorer service/Region/component evidence
- paid/zero-cost/supporting/unbilled classifications
- inferred resource relationships

B) LIVE AWS READ QUERY
Live AWS MCP is only needed for current state or details that are not present
in the baseline saved snapshot.

Return:
- service: AWS SDK service identifier when known/relevant, otherwise ""
- operation: "SnapshotLookup" for snapshot questions; otherwise one REAL
  read-only AWS API operation in PascalCase
- region: explicit user-selected/requested Region only, otherwise null
- params_json: JSON OBJECT encoded as a STRING, or exactly "{}"
- resource_id: selected/explicit resource identifier when unambiguous, else null
- operation is the routing signal: use exactly "SnapshotLookup" for saved-snapshot
  questions; use one real read-only AWS API operation only when current/live data is required

DECISION RULES:
1. DEFAULT TO THE SAVED SNAPSHOT when the user asks about what was discovered,
   services/resources/Regions/zones, billing/cost, classification, relationships,
   or asks follow-ups about a selected item from Discovery.
2. A question such as "show EC2 resources", "what services do I have?",
   "which Regions are used?", "what did the scan find?", "what is this service
   costing?", or "tell me about this selected resource" is a SNAPSHOT question
   unless the user explicitly asks for current/live/now/latest state or an
   attribute not stored by discovery.
3. Use a real AWS API operation only when live AWS state is necessary, e.g.
   "what is its state right now?", "show its current security group rules",
   "get the latest configuration from AWS", or another detail not represented
   by baseline discovery evidence.
4. For saved-snapshot questions:
   - operation MUST be "SnapshotLookup"
   - params_json MUST be "{}"
   - do not invent an AWS API operation
5. For live questions:
   - choose exactly one real AWS read operation
   - allowed operation families include Get*, List*, Describe*, Search*,
     Lookup*, BatchGet*, Select*
   - never choose Create*, Delete*, Put*, Update*, Modify*, Terminate*, Start*,
     Stop*, Run*, Invoke*, Attach*, Detach*, Enable*, Disable*, Register*,
     Deregister*, Set*, Tag*, Untag*
6. Never invent Regions, resources, identifiers, services, or operation names.
7. Structured selected context identifies the saved item the user clicked and
   may be used to resolve "this", "it", "that resource", etc.
8. Conversation history is reference context only; it is not current AWS state.

EXAMPLES:

User: what services were discovered?
service = ""
operation = SnapshotLookup
region = null
params_json = "{}"
resource_id = null
User: show EC2 resources from this scan
service = ec2
operation = SnapshotLookup
region = null
params_json = "{}"
resource_id = null
User after clicking a resource: tell me everything the scan knows about this
service = <selected service when present>
operation = SnapshotLookup
region = <selected region when present>
params_json = "{}"
resource_id = <selected resource id when present>
User: what is the current state of instance i-123 right now?
service = ec2
operation = DescribeInstances
region = null
params_json = "{\"InstanceIds\":[\"i-123\"]}"
resource_id = i-123
'''

        context_text = (conversation_context or "").strip()[-6000:]
        selected_context_text = json.dumps(selected_context or {}, default=str)
        user_prompt = f"""
Structured discovery selection:
{selected_context_text}

Recent conversation context:
{context_text}

Current user question:
{question}
"""

        response = self._client.chat.completions.create(
            model=settings.groq_intent_model,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "aws_query_intent",
                    "strict": True,
                    "schema": schema,
                },
            },
        )

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Groq returned an empty intent response.")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Groq returned invalid JSON for AWS intent.") from exc

        # Do not ask the model to emit a JSON boolean for routing. Some Groq
        # models occasionally serialize booleans as strings even under strict
        # structured output, causing the provider to reject the entire response
        # before the application can validate it. The operation already provides
        # an unambiguous routing signal, so derive the boolean deterministically.
        operation = str(data.get("operation") or "").strip()
        data["requires_live_data"] = operation.lower() != "snapshotlookup"

        return AWSQueryIntent(**data)
