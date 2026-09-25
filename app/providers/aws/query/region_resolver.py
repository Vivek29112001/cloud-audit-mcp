from __future__ import annotations
from typing import Any

class AWSQueryRegionResolver:
    def resolve(self, *, service: str, requested_region: str | None, service_entry: dict[str, Any] | None, fallback_region: str) -> list[str]:
        if requested_region: return [requested_region]
        if service_entry:
            regions=[r for r in service_entry.get("regions",[]) if r and r!="global"]
            if regions:return sorted(set(regions))
        return [fallback_region] if fallback_region else []
