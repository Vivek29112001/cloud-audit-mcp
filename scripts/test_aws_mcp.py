import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.mcp_client import AWSMCPClient


async def main() -> None:
    access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    session_token = os.getenv("AWS_SESSION_TOKEN")

    if not access_key_id:
        raise RuntimeError(
            "AWS_ACCESS_KEY_ID is not configured."
        )

    if not secret_access_key:
        raise RuntimeError(
            "AWS_SECRET_ACCESS_KEY is not configured."
        )

    credentials = AWSCredentials(
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        session_token=session_token,
        default_region="us-east-1",
    )

    client = AWSMCPClient(credentials)

    tools = await client.list_tools()

    print("\nAWS MCP connection successful.")
    print(f"Tools discovered: {len(tools)}")

    for tool in tools:
        print(f"- {tool.name}")


if __name__ == "__main__":
    asyncio.run(main())