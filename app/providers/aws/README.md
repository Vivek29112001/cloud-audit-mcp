AWS Integration Rule

This application does not communicate directly with AWS APIs.

All AWS operations MUST pass through:

AWSMCPClient
→
Official AWS Managed MCP Server
→
aws\_\_\_run_script
→
AWS API

Forbidden inside application code:

- boto3.client(...)
- boto3.resource(...)
- subprocess AWS CLI commands
- direct AWS REST/API calls
- custom MCP server implementations

The call_boto3 helper is permitted only inside Python
scripts sent to the official AWS MCP Server.
