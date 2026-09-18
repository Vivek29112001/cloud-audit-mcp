# AWS Provider Integration Rule

This application does not communicate directly with AWS APIs.

All AWS operations MUST pass through:

```text
AWSMCPClient
    ->
Official AWS Managed MCP Server
    ->
aws___run_script
    ->
AWS API
```

Forbidden inside application code:

- `boto3.client(...)`
- `boto3.resource(...)`
- subprocess AWS CLI scanning
- direct AWS REST/API calls
- custom MCP server implementations

The `call_boto3` helper is permitted only inside Python scripts sent to
the official AWS Managed MCP Server.

## Baseline discovery performance design

The baseline discovery scan intentionally collects only:

- caller/account identity
- enabled/disabled Regions
- Availability Zones
- lightweight Resource Explorer metadata
- detected services and used Regions

Detailed EC2, S3, RDS, IAM, Lambda, EKS, and other configuration is fetched
later on demand from the NLP query flow.

For performance, the discovery orchestrator opens one reusable `AWSMCPClient`
session for the whole scan:

```text
Open MCP session once
    ->
GetCallerIdentity
    ->
DescribeRegions
    ->
Availability Zone discovery
    ->
bounded concurrent Resource Explorer discovery
    ->
aggregate service/resource metadata
    ->
close MCP session
```

Resource Explorer regional work uses bounded concurrency rather than an
unbounded fan-out. The current limit is `5` Regions at a time in
`AWSResourceDiscoveryService.MAX_CONCURRENT_REGIONS`.

The scan response also includes stage timings:

```text
identity_ms
regions_ms
zones_ms
resource_discovery_ms
total_ms
```

Use these timings to identify the actual bottleneck before changing concurrency.
