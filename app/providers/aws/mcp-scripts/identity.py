from __future__ import annotations


def build_identity_script() -> str:
    """
    Build the Python script that will be executed inside the
    official AWS Managed MCP Server.

    This script does NOT execute locally.

    Flow:
        Our application
            -> AWSMCPClient
            -> Official AWS Managed MCP Server
            -> run_script
            -> call_boto3
            -> STS GetCallerIdentity
    """

    return """
identity = await call_boto3(
    service_name="sts",
    operation_name="GetCallerIdentity",
    region_name="us-east-1",
    params={}
)

result = {
    "Account": identity.get("Account"),
    "Arn": identity.get("Arn"),
    "UserId": identity.get("UserId")
}

result
"""