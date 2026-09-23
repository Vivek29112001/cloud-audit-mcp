## Phase 1 target

#### The end result of Phase 1 should behave like this:

Client
│
│ Access Key + Secret Key
▼
XYZ Audit Platform
│
├── Validate AWS credentials
│
├── Identify AWS account
│
├── Discover enabled Regions
│
├── Discover Availability Zones
│
├── Discover actual resources/services
│
├── Build dynamic inventory
│
├── Store normalized snapshot
│
└── Allow NLP questions
│
▼
Groq LLM
│
▼
Query Router
│
┌─────┴─────┐
│ │
▼ ▼
Inventory AWS MCP
snapshot live check
│ │
└─────┬─────┘
▼
Grounded Answer

Our architecture becomes:

┌───────────────────────────────────────────────┐
│ XYZ AWS AUDITOR │
└───────────────────────────────────────────────┘

                     USER
                      │
                      ▼
              Streamlit UI
                      │
                      ▼
                 FastAPI
                      │
                      ▼
            AWS Credential Manager
                      │
                      ▼
               Scan Orchestrator
                      │
                      ▼
                  MCP Client
                      │
                      ▼
          AWS Managed MCP Server
                      │
                      ▼
                   AWS APIs
                      │
                      ▼
           Dynamic AWS Infrastructure
                      │
                      ▼
              Scan Orchestrator
                      │
                normalize
                      │
                      ▼
                 PostgreSQL
                      │
                      ▼
                 NLP Layer
                      │
                    Groq
                      │
              ┌───────┴────────┐
              │                │
              ▼                ▼
        Inventory query    Live MCP query
              │                │
              └───────┬────────┘
                      ▼
                 Final Answer

# Cloud Audit MCP

AI-assisted cloud infrastructure discovery and auditing platform built around the Model Context Protocol (MCP).

The project connects to customer cloud environments using authorized read-only credentials, dynamically discovers cloud infrastructure, builds a normalized inventory, and enables natural-language queries against the discovered infrastructure.

## Current Status

**Phase 1: AWS**

Current development focuses exclusively on AWS.

Future phases will introduce:

- Microsoft Azure
- Google Cloud Platform
- Security posture checks
- Compliance frameworks
- RAG-based compliance knowledge
- Cross-cloud inventory
- Infrastructure relationship analysis

---

## Project Goal

The objective is to create a cloud auditing platform where an auditor can connect a customer's cloud account and dynamically discover:

- Cloud account identity
- Enabled Regions
- Availability Zones
- Regions actually containing resources
- Services actively being used
- Cloud resources
- Resource configurations
- Network configuration
- IAM configuration
- Security-related metadata

Auditors will then be able to ask questions about the discovered infrastructure using natural language.

Example questions:

```text
Which AWS Regions are being used?

Which services exist in ap-south-1?

How many EC2 instances are running?

Which Availability Zones contain resources?

Show all RDS databases.

Which EC2 instances have public IP addresses?

Is EC2 instance i-123456 currently running?
```

Answers must be generated from actual cloud-account evidence rather than static or predefined infrastructure data.

---

# Architecture

```text
                        Auditor
                           │
                           ▼
                     Streamlit UI
                           │
                           ▼
                       FastAPI
                           │
                           ▼
                  Scan Orchestrator
                           │
                           ▼
                      MCP Client
                           │
                           ▼
                 AWS MCP Proxy / SigV4
                           │
                           ▼
                 AWS Managed MCP Server
                           │
                           ▼
                       AWS APIs
                           │
                           ▼
                  Client AWS Account
                           │
                           ▼
                 Dynamic Discovery
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
          Regions         Zones       Resources
             │             │             │
             └─────────────┼─────────────┘
                           ▼
                    Normalized Inventory
                           │
                           ▼
                       Database
                           │
                      ┌────┴────┐
                      ▼         ▼
                    Groq       MCP
                    NLP        Live Query
                      │         │
                      └────┬────┘
                           ▼
                       Response
```

---

# Design Principles

## Dynamic Discovery

No customer infrastructure information should be statically defined.

The application dynamically retrieves:

```text
Account
Regions
Availability Zones
Services
Resources
Configurations
```

from the authenticated customer's AWS account.

For example, the application must not contain:

```python
regions = [
    "us-east-1",
    "ap-south-1"
]
```

Instead, Regions are retrieved dynamically from AWS.

---

## MCP-First AWS Integration

Phase 1 follows an MCP-first architecture.

```text
Application
     │
     ▼
MCP Client
     │
     ▼
AWS Managed MCP Server
     │
     ▼
AWS APIs
```

The application does not use boto3 as its primary AWS integration layer.

AWS CLI is intended only for development and debugging where necessary.

---

## Deterministic Scanning

The Large Language Model does not decide how infrastructure scanning works.

Scanning is controlled by deterministic application logic:

```text
Verify Account
      ↓
Discover Regions
      ↓
Discover Availability Zones
      ↓
Discover Resources
      ↓
Determine Used Regions
      ↓
Determine Used Services
      ↓
Collect Resource Configuration
      ↓
Normalize
      ↓
Store Inventory
```

This ensures scans remain predictable and auditable.

---

## AI Responsibilities

Groq or another LLM is used for:

- Natural-language understanding
- Intent classification
- Parameter extraction
- Query routing
- Answer generation
- Explanation

The LLM is not treated as the source of truth.

AWS remains the infrastructure source of truth.

---

# Phase 1

Phase 1 focuses on AWS.

## Phase 1 Scope

### AWS Connection

- Accept AWS Access Key ID
- Accept AWS Secret Access Key
- Optional AWS Session Token
- Validate credentials
- Identify AWS Account
- Retrieve caller identity

### Region Discovery

Dynamically retrieve:

- Region name
- Region endpoint
- Opt-in status
- Enabled/disabled state

Possible AWS Region states include:

```text
opt-in-not-required
opted-in
not-opted-in
```

### Availability Zone Discovery

For every enabled Region dynamically retrieve:

- Availability Zone name
- Zone ID
- Region
- Zone state
- Zone type
- Opt-in status

### Resource Discovery

Future Phase 1 implementation will identify actual resources in the connected account.

Examples include:

```text
EC2
VPC
S3
RDS
Lambda
IAM
CloudWatch
EKS
ECS
DynamoDB
```

The application will not assume that these services exist.

Services are derived from discovered resources.

### Used Region Detection

An enabled Region does not necessarily contain customer infrastructure.

The system therefore distinguishes between:

```text
Enabled Region
```

and:

```text
Used Region
```

A Region becomes a used Region only when relevant account resources are discovered there.

### Service Detection

Services are derived from discovered AWS resources.

Example:

```text
AWS::EC2::Instance
AWS::RDS::DBInstance
AWS::Lambda::Function
```

becomes:

```text
EC2
RDS
Lambda
```

### Natural Language Querying

After inventory creation, an auditor will be able to ask questions such as:

```text
Which Regions are being used?

Which services exist in Mumbai?

How many EC2 instances exist?

Show all databases.

Which resources exist in us-east-1?
```

The LLM will query discovered inventory rather than generate answers from general model knowledge.

---

# Technology Stack

| Layer           | Technology                          |
| --------------- | ----------------------------------- |
| Language        | Python                              |
| Environment     | uv                                  |
| Backend         | FastAPI                             |
| UI              | Streamlit                           |
| Cloud protocol  | MCP                                 |
| AWS integration | AWS Managed MCP Server              |
| MCP SDK         | Official MCP Python SDK             |
| Authentication  | AWS SigV4                           |
| AI/NLP          | Groq                                |
| Validation      | Pydantic                            |
| Configuration   | pydantic-settings                   |
| Database        | SQLite initially / PostgreSQL later |

---

# Project Structure

```text
cloud-audit-mcp/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── aws.py
│   │   ├── health.py
│   │   └── schemas/
│   │       └── aws.py
│   │
│   ├── core/
│   │   └── config.py
│   │
│   └── providers/
│       └── aws/
│           ├── connection.py
│           ├── credentials.py
│           ├── exceptions.py
│           ├── mcp_client.py
│           ├── models.py
│           ├── regions.py
│           ├── zones.py
│           ├── result_parser.py
│           └── scanner.py
│
├── ui/
│   └── app.py
│
├── scripts/
│   └── test_aws_mcp.py
│
├── tests/
│
├── docs/
│   ├── architecture.md
│   ├── phase-1.md
│   └── security.md
│
├── .env.example
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md
```

---

# Local Setup

## Prerequisites

Install:

- Git
- Python 3.13
- uv
- AWS account with read-only auditing permissions

Verify:

```bash
git --version
python --version
uv --version
```

---

## Clone Repository

```bash
git clone <repository-url>

cd cloud-audit-mcp
```

---

## Create Environment

```bash
uv venv --python 3.13
```

### Windows

```powershell
.venv\Scripts\activate
```

### Linux/macOS

```bash
source .venv/bin/activate
```

---

## Install Dependencies

```bash
uv sync
```

---

## Configure Environment

Copy:

```text
.env.example
```

to:

```text
.env
```

Example:

```env
APP_NAME=XYZ Cloud Audit MCP
APP_ENV=development

AWS_MCP_ENDPOINT=https://aws-mcp.us-east-1.api.aws/mcp
AWS_MCP_ENDPOINT_REGION=us-east-1

MCP_READ_ONLY=true
MCP_TIMEOUT=180
MCP_TOOL_TIMEOUT=300

GROQ_API_KEY=
```

Do not store customer AWS credentials in `.env`.

---

# Run Backend

```bash
uv run uvicorn app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

Health:

```text
GET /api/health
```

---

# Run Streamlit

In another terminal:

```bash
uv run streamlit run ui/app.py
```

---

# Current APIs

## Verify AWS Account

```text
POST /api/aws/verify
```

Request:

```json
{
  "access_key_id": "CLIENT_ACCESS_KEY",
  "secret_access_key": "CLIENT_SECRET_KEY",
  "session_token": null
}
```

Response:

```json
{
  "provider": "AWS",
  "account_id": "123456789012",
  "arn": "arn:aws:iam::123456789012:user/audit-user",
  "user_id": "AIDAXXXXX",
  "connection_status": "VERIFIED"
}
```

Credentials must never be included in the response.

---

## Discover AWS Regions

```text
POST /api/aws/regions
```

The Region list is retrieved dynamically from AWS.

Example response:

```json
{
  "total_regions": 0,
  "enabled_regions": 0,
  "disabled_regions": 0,
  "regions": []
}
```

Actual values depend entirely on the connected AWS account and current AWS Region availability.

---

# Security

This project handles sensitive customer cloud credentials.

The following rules are mandatory.

## Never Commit Credentials

Never commit:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN
GROQ_API_KEY
customer infrastructure data
raw scan evidence
```

The following paths are ignored by Git:

```text
.env
.aws/
scan-output/
raw-evidence/
```

---

## Read-Only Access

Phase 1 operates in read-only mode.

The application must not intentionally:

```text
Create resources
Modify resources
Delete resources
Terminate instances
Change IAM policies
Change security groups
Modify customer configuration
```

The auditing principal should follow least-privilege principles.

---

## AI Credential Isolation

Customer credentials must never be sent to an LLM.

Correct flow:

```text
Credentials
    ↓
AWS MCP
    ↓
AWS
```

Incorrect flow:

```text
Credentials
    ↓
Groq
```

Groq should receive only the minimum infrastructure context required to answer an auditor's question.

---

# Development Roadmap

## Phase 1 — AWS Discovery

- [x] Project setup
- [x] uv environment
- [x] FastAPI foundation
- [x] Streamlit foundation
- [x] MCP client
- [x] AWS credential verification
- [x] AWS account identity
- [x] Dynamic Region discovery
- [ ] Dynamic Availability Zone discovery
- [ ] Dynamic resource discovery
- [ ] Used Region detection
- [ ] Service detection
- [ ] Resource normalization
- [ ] Inventory persistence
- [ ] Scan orchestration
- [ ] Groq integration
- [ ] NLP query routing
- [ ] Inventory-based Q&A
- [ ] Live MCP queries

## Phase 2 — Security Analysis

Planned capabilities:

- Security group analysis
- Public resource detection
- Storage configuration
- Encryption checks
- IAM analysis
- Network exposure
- Security findings
- Deterministic policy engine

## Phase 3 — Compliance Intelligence

Planned capabilities:

- CIS
- ISO 27001
- PCI DSS
- SOC 2
- Internal security controls
- RAG-based compliance knowledge

## Phase 4 — Multi-Cloud

Planned providers:

```text
AWS
Azure
GCP
```

Provider-specific integrations will implement a shared cloud-provider abstraction.

---

# Long-Term Architecture

```text
CloudProvider
      │
      ├── AWSProvider
      │       ↓
      │     AWS MCP
      │
      ├── AzureProvider
      │       ↓
      │    Azure MCP
      │
      └── GCPProvider
              ↓
           GCP MCP
```

The AI layer should operate against normalized cloud inventory rather than provider-specific raw structures.

---

# Disclaimer

This project is intended for authorized cloud-security auditing only.

Only connect accounts where the organization has explicit authorization to inspect the target cloud environment.
"# cloud-audit-mcp"

# AWS Phase 1 updated backend

This bundle contains the corrected MCP-only AWS Phase-1 backend modules through
the EC2/VPC/EBS deep-collector step.

## Main fixes

- `AwsCredentials` -> `AWSCredentials`
- `AWSColectorRegistry` -> `AWSCollectorRegistry`
- completed `EC2MCPCollector._collect_region()`
- added EC2 instance, security-group, EBS, subnet and route-table collection
- added `AWSDeepScanService`
- added collector factory
- added typed API request/response schemas
- added `/api/aws/deep-scan`
- normalized result parsing
- kept AWS access through MCP only

## Expected project paths

Copy the `app/` folder content into your existing project while keeping your
existing `app/core/config.py`.

Your `app/main.py` should include:

```python
from fastapi import FastAPI
from app.api.aws import router as aws_router
```

---

## Dynamic Billing-Aware Service / Region Classification

The AWS scan now correlates three independent evidence sources instead of using a hard-coded service catalog:

1. **Resource Explorer** - what resources/services currently exist.
2. **Cost Explorer** - which billing services and Regions have actual `UnblendedCost`.
3. **Resource property references** - generic ARN/resource-ID relationships discovered from Resource Explorer properties.

### Classification rules

- `PRIMARY_PAID`: a dynamically discovered service matched to one or more Cost Explorer `SERVICE` values whose combined cost is greater than zero.
- `PRIMARY_PAID_BILLING_ONLY`: a Cost Explorer service with positive cost that cannot be reliably matched to a Resource Explorer service. It is retained rather than discarded.
- `SUPPORTING_RELATED`: a discovered service with no positive direct cost that has a resource-reference relationship to a paid discovered service.
- `DISCOVERED_UNBILLED`: a discovered service with no positive direct cost and no proven relationship to a paid service.
- `PAID_PRIMARY`: a Region with positive Cost Explorer cost.
- `USED_UNBILLED`: a Region containing discovered resources but no positive billing amount in the selected billing period.
- `ENABLED_UNUSED`: an enabled Region with neither discovered resources nor positive billing amount.

The matcher does **not** contain mappings such as `EC2 -> Amazon Elastic Compute Cloud` or `S3 -> Amazon Simple Storage Service`. It derives candidate aliases from the live billing service name itself using normalization, contiguous words, and acronym/run-length generation. Uncertain names remain billing-only instead of being force-matched.

### Billing period

The scan uses the current calendar month up to today (end date is exclusive because Cost Explorer data is not real-time). On the first day of a month, the previous full month is used.

### Additional read-only IAM permissions

To enable billing classification, the supplied audit principal must be allowed to call:

```json
{
  "Effect": "Allow",
  "Action": [
    "ce:GetCostAndUsage",
    "ce:GetDimensionValues"
  ],
  "Resource": "*"
}
```

If these permissions are absent, the infrastructure scan still completes and returns `billing.available=false` with a warning. No AWS credentials are persisted by this feature.

### New response sections

`POST /api/aws/scan` and `GET /api/aws/scans/{scan_id}` now include:

```text
billing
classification
  primary_paid_services
  supporting_services
  discovered_unbilled_services
  non_positive_billing_services
  paid_regions
  used_unbilled_regions
  enabled_unused_regions
  billed_only_regions
  relationships
```

### Database migration

Run before starting an upgraded existing installation:

```bash
alembic upgrade head
```

This adds `billing_json` and `classification_json` to `aws_scans`.
