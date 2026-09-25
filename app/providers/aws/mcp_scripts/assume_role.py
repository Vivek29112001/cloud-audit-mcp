from __future__ import annotations


def build_assume_role_script(
    *,
    role_arn: str,
    role_session_name: str,
    duration_seconds: int,
    external_id: str | None,
) -> str:
    params = {
        "RoleArn": role_arn,
        "RoleSessionName": role_session_name,
        "DurationSeconds": duration_seconds,
    }
    if external_id:
        params["ExternalId"] = external_id

    return f'''
params = {params!r}
response = await call_boto3(
    service_name="sts",
    operation_name="AssumeRole",
    region_name="us-east-1",
    params=params,
)
credentials = response.get("Credentials") or {{}}
assumed_role_user = response.get("AssumedRoleUser") or {{}}
result = {{
    "AccessKeyId": credentials.get("AccessKeyId"),
    "SecretAccessKey": credentials.get("SecretAccessKey"),
    "SessionToken": credentials.get("SessionToken"),
    "Expiration": credentials.get("Expiration"),
    "AssumedRoleArn": assumed_role_user.get("Arn"),
    "AssumedRoleId": assumed_role_user.get("AssumedRoleId"),
}}
result
'''
