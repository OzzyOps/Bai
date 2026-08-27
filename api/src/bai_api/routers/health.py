from __future__ import annotations

from fastapi import APIRouter

from bai_api.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness. Deliberately reveals nothing about configuration."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready() -> dict[str, object]:
    """Readiness. Reports which regions are configured, never their credentials."""
    s = get_settings()
    return {
        "status": "ready",
        "environment": s.environment,
        "regions": sorted(s.supabase_urls),
    }
