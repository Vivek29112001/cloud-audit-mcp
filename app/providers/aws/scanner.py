from __future__ import annotations
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4
from app.providers.aws.billing import AWSBillingDiscoveryService
from app.providers.aws.classification import AWSInfrastructureClassificationService
from app.providers.aws.connection import AWSConnectionService
from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.discovery import AWSResourceDiscoveryService
from app.providers.aws.mcp_client import AWSMCPClient
from app.providers.aws.models import AWSScanResult, AWSScanSummary
from app.providers.aws.regions import AWSRegionService
from app.providers.aws.zones import AWSZoneService


class AWSScanOrchestrator:
    def __init__(self):
        self.connection_service=AWSConnectionService(); self.region_service=AWSRegionService(); self.zone_service=AWSZoneService(); self.resource_service=AWSResourceDiscoveryService(); self.billing_service=AWSBillingDiscoveryService(); self.classification_service=AWSInfrastructureClassificationService()

    async def scan(self, credentials: AWSCredentials) -> AWSScanResult:
        started=perf_counter(); timings={}; result=AWSScanResult(scan_id=str(uuid4()),status="RUNNING",started_at=datetime.now(timezone.utc))
        try:
            async with AWSMCPClient(credentials) as mcp:
                t=perf_counter(); identity=await self.connection_service.verify_credentials(mcp=mcp); timings["identity_ms"]=self._elapsed_ms(t); result.account=identity
                t=perf_counter(); regions=await self.region_service.discover_regions(mcp=mcp); timings["regions_ms"]=self._elapsed_ms(t); result.regions=regions
                enabled=[r.region_name for r in regions.regions if r.enabled]
                t=perf_counter(); zones=await self.zone_service.discover_zones(enabled_regions=enabled,mcp=mcp); timings["zones_ms"]=self._elapsed_ms(t); result.zones=zones
                t=perf_counter(); resources=await self.resource_service.discover_resources(enabled_regions=enabled,mcp=mcp); timings["resource_discovery_ms"]=self._elapsed_ms(t); result.resources=resources; result.warnings.extend(resources.warnings)
                t=perf_counter(); billing=await self.billing_service.discover_billing(mcp=mcp); timings["billing_discovery_ms"]=self._elapsed_ms(t); result.billing=billing; result.warnings.extend(billing.warnings)
                t=perf_counter(); classification=self.classification_service.classify(regions=regions,resources=resources,billing=billing); timings["classification_ms"]=self._elapsed_ms(t); result.classification=classification
                result.summary=AWSScanSummary(account_id=identity.account_id,enabled_regions=regions.enabled_regions,disabled_regions=regions.disabled_regions,availability_zones=zones.total_zones,used_regions=len(resources.used_regions),detected_services=len(resources.detected_services),discovered_resources=resources.total_resources,billing_available=billing.available,primary_paid_services=len([x for x in classification.primary_paid_services if x.discovered_service]),zero_cost_services=len([x for x in classification.zero_cost_services if x.discovered_service]),supporting_services=len(classification.supporting_services),paid_regions=len(classification.paid_regions))
                result.status="COMPLETED"
        except Exception as exc:
            result.status="FAILED"; result.warnings.append(str(exc))
        finally:
            timings["total_ms"]=self._elapsed_ms(started); result.timings=timings; result.completed_at=datetime.now(timezone.utc)
        return result
    @staticmethod
    def _elapsed_ms(t): return round((perf_counter()-t)*1000)
