from __future__ import annotations


def build_billing_discovery_script(
    *,
    start_date: str,
    end_date: str,
) -> str:
    """
    Build a Cost Explorer discovery script executed inside AWS Managed MCP.

    The logic is intentionally data-driven:
    - no AWS service catalog is embedded in the application;
    - service names come directly from Cost Explorer SERVICE values;
    - billed components come from SERVICE + USAGE_TYPE groups;
    - billed Regions come from Cost Explorer REGION dimension values.

    Cost Explorer has a single public API endpoint in us-east-1, so the
    control-plane call uses that endpoint. This does not classify us-east-1
    as a workload Region.
    """

    return f'''
start_date = {start_date!r}
end_date = {end_date!r}
metric_name = "UnblendedCost"
ce_region = "us-east-1"


def metric_value(container):
    metric = (container or {{}}).get(metric_name, {{}})
    raw = metric.get("Amount", "0")
    try:
        amount = float(raw or 0)
    except (TypeError, ValueError):
        amount = 0.0
    return amount, metric.get("Unit") or "USD"


# ------------------------------------------------------------
# 1. Cost by billing SERVICE
# ------------------------------------------------------------
service_totals = {{}}
service_units = {{}}
next_token = None

while True:
    params = {{
        "TimePeriod": {{
            "Start": start_date,
            "End": end_date,
        }},
        "Granularity": "MONTHLY",
        "Metrics": [metric_name],
        "GroupBy": [
            {{
                "Type": "DIMENSION",
                "Key": "SERVICE",
            }}
        ],
    }}

    if next_token:
        params["NextPageToken"] = next_token

    response = await call_boto3(
        service_name="ce",
        operation_name="GetCostAndUsage",
        region_name=ce_region,
        params=params,
    )

    for period in response.get("ResultsByTime", []):
        for group in period.get("Groups", []):
            keys = group.get("Keys") or []
            if not keys:
                continue
            service_name = keys[0]
            amount, unit = metric_value(group.get("Metrics"))
            service_totals[service_name] = (
                service_totals.get(service_name, 0.0) + amount
            )
            service_units[service_name] = unit

    next_token = response.get("NextPageToken")
    if not next_token:
        break


# ------------------------------------------------------------
# 2. Dynamic billed components using SERVICE + USAGE_TYPE
# ------------------------------------------------------------
component_totals = {{}}
component_units = {{}}
next_token = None

while True:
    params = {{
        "TimePeriod": {{
            "Start": start_date,
            "End": end_date,
        }},
        "Granularity": "MONTHLY",
        "Metrics": [metric_name],
        "GroupBy": [
            {{
                "Type": "DIMENSION",
                "Key": "SERVICE",
            }},
            {{
                "Type": "DIMENSION",
                "Key": "USAGE_TYPE",
            }},
        ],
    }}

    if next_token:
        params["NextPageToken"] = next_token

    response = await call_boto3(
        service_name="ce",
        operation_name="GetCostAndUsage",
        region_name=ce_region,
        params=params,
    )

    for period in response.get("ResultsByTime", []):
        for group in period.get("Groups", []):
            keys = group.get("Keys") or []
            if len(keys) < 2:
                continue
            service_name = keys[0]
            usage_type = keys[1]
            amount, unit = metric_value(group.get("Metrics"))
            pair_key = (service_name, usage_type)
            component_totals[pair_key] = (
                component_totals.get(pair_key, 0.0) + amount
            )
            component_units[pair_key] = unit

    next_token = response.get("NextPageToken")
    if not next_token:
        break


# ------------------------------------------------------------
# 3. Discover only Regions that occur in billing data
# ------------------------------------------------------------
region_values = []
next_token = None

while True:
    params = {{
        "TimePeriod": {{
            "Start": start_date,
            "End": end_date,
        }},
        "Context": "COST_AND_USAGE",
        "Dimension": "REGION",
    }}

    if next_token:
        params["NextPageToken"] = next_token

    response = await call_boto3(
        service_name="ce",
        operation_name="GetDimensionValues",
        region_name=ce_region,
        params=params,
    )

    for item in response.get("DimensionValues", []):
        value = item.get("Value")
        if value and value not in region_values:
            region_values.append(value)

    next_token = response.get("NextPageToken")
    if not next_token:
        break


# ------------------------------------------------------------
# 4. Cost per dynamically discovered billing Region
# ------------------------------------------------------------
region_costs = []

for billing_region in region_values:
    amount_total = 0.0
    unit = "USD"
    next_token = None

    while True:
        params = {{
            "TimePeriod": {{
                "Start": start_date,
                "End": end_date,
            }},
            "Granularity": "MONTHLY",
            "Metrics": [metric_name],
            "Filter": {{
                "Dimensions": {{
                    "Key": "REGION",
                    "Values": [billing_region],
                }}
            }},
        }}

        if next_token:
            params["NextPageToken"] = next_token

        response = await call_boto3(
            service_name="ce",
            operation_name="GetCostAndUsage",
            region_name=ce_region,
            params=params,
        )

        for period in response.get("ResultsByTime", []):
            amount, period_unit = metric_value(period.get("Total"))
            amount_total += amount
            unit = period_unit or unit

        next_token = response.get("NextPageToken")
        if not next_token:
            break

    region_costs.append({{
        "Region": billing_region,
        "Amount": amount_total,
        "Unit": unit,
    }})


service_costs = [
    {{
        "Service": name,
        "Amount": amount,
        "Unit": service_units.get(name, "USD"),
    }}
    for name, amount in service_totals.items()
]

components = []
for pair_key, amount in component_totals.items():
    service_name, usage_type = pair_key
    components.append({{
        "Service": service_name,
        "UsageType": usage_type,
        "Amount": amount,
        "Unit": component_units.get(pair_key, "USD"),
    }})

result = {{
    "TimePeriod": {{
        "Start": start_date,
        "End": end_date,
    }},
    "Metric": metric_name,
    "ServiceCosts": service_costs,
    "Components": components,
    "RegionCosts": region_costs,
}}

result
'''
