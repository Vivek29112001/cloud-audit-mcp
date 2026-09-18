from __future__ import annotations

import json

from groq import Groq

from app.ai.intent_models import AWSQueryIntent
from app.core.config import settings


class GroqIntentClient:
    def __init__(self) -> None:
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not configured."
            )

        self._client = Groq(
            api_key=settings.groq_api_key
        )

    def parse_aws_question(
        self,
        question: str,
    ) -> AWSQueryIntent:
        """
        Convert a natural-language AWS question into ONE safe read-only AWS
        API operation. The returned plan is validated by AWSQueryIntent and is
        still subject to the backend read-only operation validator before MCP
        execution.
        """

        schema = {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                },
                "operation": {
                    "type": "string",
                },
                "region": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
                "params_json": {
                    "type": "string",
                },
                "resource_id": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
                "requires_live_data": {
                    "type": "boolean",
                },
            },
            "required": [
                "service",
                "operation",
                "region",
                "params_json",
                "resource_id",
                "requires_live_data",
            ],
            "additionalProperties": False,
        }

        system_prompt = r'''
You are the query planner for a read-only AWS infrastructure auditing
application.

Your job is ONLY to convert the user's question into one real AWS read API
operation. Do not answer the infrastructure question yourself.

Return these fields:
- service: AWS SDK service identifier, for example ec2, rds, lambda,
  dynamodb, iam, s3, eks, ecs, cloudtrail, kms.
- operation: one REAL AWS API operation in PascalCase.
- region: only when the user explicitly specifies a Region; otherwise null.
- params_json: a STRING containing a valid JSON object for AWS API parameters.
- resource_id: a resource identifier only when the user explicitly provides
  one; otherwise null.
- requires_live_data: normally true for account/infrastructure questions.

CRITICAL RULES:
1. Never invent AWS API operation names.
2. Only choose read-only operations such as Get*, List*, Describe*, Search*,
   Lookup*, BatchGet*, Select*.
3. Never choose write/change operations such as Create*, Delete*, Put*,
   Update*, Modify*, Terminate*, Start*, Stop*, Run*, Invoke*, Attach*,
   Detach*, Enable*, Disable*, Register*, Deregister*, Set*, Tag*, Untag*.
4. params_json MUST be a JSON STRING. When no parameters are required, return
   exactly "{}".
5. Do not invent Regions or resource IDs.
6. If a question needs several API operations, choose the primary read
   operation only. A later complex-query workflow will handle multi-call
   correlation.

Correct examples:

User: show all ec2 instances
service = ec2
operation = DescribeInstances
region = null
params_json = "{}"
resource_id = null
requires_live_data = true

User: show my VPCs
service = ec2
operation = DescribeVpcs
region = null
params_json = "{}"
resource_id = null
requires_live_data = true

User: show rds databases
service = rds
operation = DescribeDBInstances
region = null
params_json = "{}"
resource_id = null
requires_live_data = true

User: show lambda functions
service = lambda
operation = ListFunctions
region = null
params_json = "{}"
resource_id = null
requires_live_data = true

User: show dynamodb tables
service = dynamodb
operation = ListTables
region = null
params_json = "{}"
resource_id = null
requires_live_data = true

User: show IAM users
service = iam
operation = ListUsers
region = null
params_json = "{}"
resource_id = null
requires_live_data = true

User: show EKS clusters
service = eks
operation = ListClusters
region = null
params_json = "{}"
resource_id = null
requires_live_data = true

User: show ECS clusters
service = ecs
operation = ListClusters
region = null
params_json = "{}"
resource_id = null
requires_live_data = true

User: show instance i-1234567890
service = ec2
operation = DescribeInstances
region = null
params_json = "{\"InstanceIds\":[\"i-1234567890\"]}"
resource_id = i-1234567890
requires_live_data = true
'''

        response = self._client.chat.completions.create(
            model=settings.groq_intent_model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": question,
                },
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

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not content:
            raise RuntimeError(
                "Groq returned an empty intent response."
            )

        data = json.loads(content)
        return AWSQueryIntent(**data)
