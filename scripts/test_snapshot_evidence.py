from datetime import datetime, timezone
import json
from app.ai.snapshot_evidence import build_snapshot_evidence
scan={"scan_id":"scan-test","status":"COMPLETED","completed_at":datetime.now(timezone.utc),"account":{"account_id":"123"},"summary":{"detected_services":1},"regions":{"regions":[{"region_name":"ap-south-1","enabled":True}]},"zones":{"zones":[]},"resources":{"total_resources":1,"used_regions":["ap-south-1"],"detected_services":[{"service":"ec2","resource_count":1,"regions":["ap-south-1"]}],"resources":[{"resource_id":"i-123","service":"ec2","region":"ap-south-1","arn":"arn:aws:ec2:ap-south-1:123:instance/i-123","properties":[{"huge":"x"*10000}]}]},"billing":{"service_costs":[],"region_costs":[],"components":[]},"classification":{"primary_paid_services":[],"zero_cost_services":[],"supporting_services":[],"discovered_unbilled_services":[],"billing_only_services":[],"non_positive_billing_services":[],"paid_regions":[],"used_unbilled_regions":[],"enabled_unused_regions":[],"billed_only_regions":[],"relationships":[]},"warnings":[]}
e=build_snapshot_evidence(scan_result=scan,selected_context={"resource_id":"i-123","service":"ec2"},intent={"service":"ec2","operation":"SnapshotLookup","resource_id":"i-123","region":None})
assert e["resources"]["matching_resources"][0]["resource_id"]=="i-123"
json.dumps(e)
assert len(json.dumps(e))<30000
print("snapshot evidence tests passed")
