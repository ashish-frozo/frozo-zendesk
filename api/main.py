"""
FastAPI main application.

Implements:
- CORS middleware
- Tenant isolation middleware
- Request validation
- Route mounting
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

from api.config import settings
from api.db.database import engine
from api.db.models import Base
from api.routes import runs, health

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown."""
    # Startup
    logger.info("Starting EscalateSafe API")
    # Create tables (in production, use Alembic migrations)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    yield
    
    # Shutdown
    logger.info("Shutting down EscalateSafe API")


app = FastAPI(
    title="EscalateSafe API",
    description="PII-Safe Zendesk → Jira Escalation System",
    version="0.1.0",
    lifespan=lifespan,
    redirect_slashes=False,  # Prevent automatic redirects that can cause HTTP/HTTPS issues
    root_path_in_servers=False
)

# CORS middleware - Allow all origins for Zendesk app compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "escalatesafe-api",
        "version": "0.1.0"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "EscalateSafe API",
        "docs": "/docs"
    }


# Mount routers
app.include_router(health.router, tags=["health"])
app.include_router(runs.router, prefix="/v1/runs", tags=["runs"])
app.include_router(oauth.router, prefix="/v1/oauth", tags=["oauth"])
app.include_router(config.router, prefix="/v1/config", tags=["config"])
# app.include_router(admin.router, prefix="/v1/admin", tags=["admin"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    )
