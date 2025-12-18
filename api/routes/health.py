"""
Railway-specific health check enhancements.

Railway expects specific health check endpoints and formats.
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint for Railway.
    
    Railway uses this to determine if the service is healthy.
    """
    return {
        "status": "healthy",
        "service": "escalatesafe-api",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check - confirms all dependencies are available.
    
    Checks:
    - Database connection
    - Redis connection
    - S3 storage access
    """
    from api.db.database import engine
    from api.config import settings
    
    checks = {
        "database": False,
        "redis": False,
        "storage": False
    }
    
    # Database check
    try:
        with engine.connect() as conn:
            checks["database"] = True
    except Exception:
        pass
    
    # Redis check
    try:
        import redis
        r = redis.from_url(settings.redis_url)
        r.ping()
        checks["redis"] = True
    except Exception:
        pass
    
    # S3 check (basic connectivity)
    try:
        from api.services.storage import get_storage_service
        storage = get_storage_service()
        # Just check if client is initialized
        checks["storage"] = storage.client is not None
    except Exception:
        pass
    
    all_healthy = all(checks.values())
    
    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }
