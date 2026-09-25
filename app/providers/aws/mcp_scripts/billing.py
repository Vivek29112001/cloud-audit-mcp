from __future__ import annotations


def build_billing_discovery_script(*, start_date: str, end_date: str) -> str:
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

service_totals = {{}}
service_units = {{}}
next_token = None
while True:
    params = {{"TimePeriod": {{"Start": start_date, "End": end_date}}, "Granularity": "MONTHLY", "Metrics": [metric_name], "GroupBy": [{{"Type": "DIMENSION", "Key": "SERVICE"}}]}}
    if next_token: params["NextPageToken"] = next_token
    response = await call_boto3(service_name="ce", operation_name="GetCostAndUsage", region_name=ce_region, params=params)
    for period in response.get("ResultsByTime", []):
        for group in period.get("Groups", []):
            keys = group.get("Keys") or []
            if not keys: continue
            name = keys[0]
            amount, unit = metric_value(group.get("Metrics"))
            service_totals[name] = service_totals.get(name, 0.0) + amount
            service_units[name] = unit
    next_token = response.get("NextPageToken")
    if not next_token: break

component_totals = {{}}
component_units = {{}}
next_token = None
while True:
    params = {{"TimePeriod": {{"Start": start_date, "End": end_date}}, "Granularity": "MONTHLY", "Metrics": [metric_name], "GroupBy": [{{"Type": "DIMENSION", "Key": "SERVICE"}}, {{"Type": "DIMENSION", "Key": "USAGE_TYPE"}}]}}
    if next_token: params["NextPageToken"] = next_token
    response = await call_boto3(service_name="ce", operation_name="GetCostAndUsage", region_name=ce_region, params=params)
    for period in response.get("ResultsByTime", []):
        for group in period.get("Groups", []):
            keys = group.get("Keys") or []
            if len(keys) < 2: continue
            pair = (keys[0], keys[1])
            amount, unit = metric_value(group.get("Metrics"))
            component_totals[pair] = component_totals.get(pair, 0.0) + amount
            component_units[pair] = unit
    next_token = response.get("NextPageToken")
    if not next_token: break

region_values = []
next_token = None
while True:
    params = {{"TimePeriod": {{"Start": start_date, "End": end_date}}, "Context": "COST_AND_USAGE", "Dimension": "REGION"}}
    if next_token: params["NextPageToken"] = next_token
    response = await call_boto3(service_name="ce", operation_name="GetDimensionValues", region_name=ce_region, params=params)
    for item in response.get("DimensionValues", []):
        value = item.get("Value")
        if value and value not in region_values: region_values.append(value)
    next_token = response.get("NextPageToken")
    if not next_token: break

region_costs = []
for billing_region in region_values:
    total = 0.0
    unit = "USD"
    next_token = None
    while True:
        params = {{"TimePeriod": {{"Start": start_date, "End": end_date}}, "Granularity": "MONTHLY", "Metrics": [metric_name], "Filter": {{"Dimensions": {{"Key": "REGION", "Values": [billing_region]}}}}}}
        if next_token: params["NextPageToken"] = next_token
        response = await call_boto3(service_name="ce", operation_name="GetCostAndUsage", region_name=ce_region, params=params)
        for period in response.get("ResultsByTime", []):
            amount, period_unit = metric_value(period.get("Total"))
            total += amount
            unit = period_unit or unit
        next_token = response.get("NextPageToken")
        if not next_token: break
    region_costs.append({{"Region": billing_region, "Amount": total, "Unit": unit}})

result = {{
    "TimePeriod": {{"Start": start_date, "End": end_date}},
    "Metric": metric_name,
    "ServiceCosts": [{{"Service": n, "Amount": a, "Unit": service_units.get(n, "USD")}} for n, a in service_totals.items()],
    "Components": [{{"Service": pair[0], "UsageType": pair[1], "Amount": a, "Unit": component_units.get(pair, "USD")}} for pair, a in component_totals.items()],
    "RegionCosts": region_costs,
}}
result
'''
