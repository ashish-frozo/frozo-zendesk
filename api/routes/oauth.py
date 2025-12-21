"""
OAuth routes for Zendesk app installation and authentication.

Handles the OAuth flow for multi-tenant Zendesk access:
1. Installation - Creates tenant and returns OAuth URL
2. Callback - Exchanges code for tokens and stores them
3. Status - Checks OAuth configuration status
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging

from api.db.database import get_db
from api.db.models import Tenant
from api.services.oauth_service import ZendeskOAuthService
from api.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class InstallRequest(BaseModel):
    """App installation request from Zendesk."""
    subdomain: str
    locale: str = "en"
    app_guid: str


@router.post("/install")
async def handle_install(
    request: InstallRequest,
    db: Session = Depends(get_db)
):
    """
    Handle app installation from Zendesk Marketplace.
    
    Creates or updates tenant record and returns OAuth authorization URL.
    This is the first step in the OAuth flow.
    
    Args:
        request: Installation details from Zendesk
        db: Database session
        
    Returns:
        Dict with authorization_url and tenant_id
    """
    try:
        logger.info(f"Installation request for subdomain: {request.subdomain}")
        
        # Check if tenant already exists
        tenant = db.query(Tenant).filter(
            Tenant.zendesk_subdomain == request.subdomain
        ).first()
        
        if not tenant:
            # Create new tenant
            tenant = Tenant(
                zendesk_subdomain=request.subdomain,
                installation_id=request.app_guid,
                installation_status="pending"
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            logger.info(f"Created new tenant {tenant.id} for {request.subdomain}")
        else:
            # Update existing tenant
            tenant.installation_id = request.app_guid
            tenant.installation_status = "pending"
            db.commit()
            logger.info(f"Updated tenant {tenant.id} for {request.subdomain}")
        
        # Build OAuth authorization URL
        redirect_uri = f"{settings.api_base_url}/v1/oauth/callback"
        auth_url = (
            f"https://{request.subdomain}.zendesk.com/oauth/authorizations/new?"
            f"response_type=code&"
            f"redirect_uri={redirect_uri}&"
            f"client_id={settings.zendesk_client_id}&"
            f"scope=read%20write&"
            f"state={tenant.id}"  # Use tenant ID as state for verification
        )
        
        return {
            "authorization_url": auth_url,
            "tenant_id": tenant.id,
            "subdomain": request.subdomain
        }
        
    except Exception as e:
        logger.error(f"Installation failed for {request.subdomain}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/callback")
async def oauth_callback(
    code: str,
    state: str,  # tenant_id
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from Zendesk after user authorization.
    
    Exchanges authorization code for access/refresh tokens and stores them.
    This is the second step in the OAuth flow.
    
    Args:
        code: Authorization code from Zendesk
        state: Tenant ID (passed as state parameter)
        db: Database session
        
    Returns:
        Redirect to success page in Zendesk
    """
    try:
        logger.info(f"OAuth callback received with state: {state}")
        
        # Get tenant from state
        tenant_id = int(state)
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        logger.info(f"Processing OAuth callback for tenant {tenant.id} ({tenant.zendesk_subdomain})")
        
        # Exchange code for tokens
        oauth_service = ZendeskOAuthService(db)
        redirect_uri = f"{settings.api_base_url}/v1/oauth/callback"
        
        tokens = oauth_service.exchange_code_for_tokens(
            code=code,
            subdomain=tenant.zendesk_subdomain,
            redirect_uri=redirect_uri
        )
        
        # Store tokens in database
        oauth_service.store_tokens(
            tenant=tenant,
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            expires_in=tokens["expires_in"],
            scope=tokens["scope"]
        )
        
        logger.info(f"OAuth flow completed successfully for tenant {tenant.id}")
        
        # Redirect to success page in Zendesk
        success_url = f"https://{tenant.zendesk_subdomain}.zendesk.com/agent/apps"
        return RedirectResponse(url=success_url)
        
    except ValueError as e:
        logger.error(f"OAuth callback validation error: {e}")
        # Redirect to error page
        error_url = f"https://frozoai.zendesk.com/agent/apps?error={str(e)}"
        return RedirectResponse(url=error_url)
        
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        # Redirect to generic error page
        error_url = "https://frozoai.zendesk.com/agent/apps?error=oauth_failed"
        return RedirectResponse(url=error_url)


@router.get("/status/{tenant_id}")
async def get_oauth_status(
    tenant_id: int,
    db: Session = Depends(get_db)
):
    """
    Check OAuth status for a tenant.
    
    Useful for debugging and checking if tenant is properly configured.
    
    Args:
        tenant_id: Tenant ID to check
        db: Database session
        
    Returns:
        Dict with OAuth status information
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return {
        "tenant_id": tenant.id,
        "subdomain": tenant.zendesk_subdomain,
        "status": tenant.installation_status,
        "has_access_token": bool(tenant.oauth_access_token),
        "has_refresh_token": bool(tenant.oauth_refresh_token),
        "token_expires_at": tenant.oauth_token_expires_at.isoformat() if tenant.oauth_token_expires_at else None,
        "scopes": tenant.oauth_scopes,
        "installed_at": tenant.installed_at.isoformat() if tenant.installed_at else None
    }


@router.get("/status")
async def get_all_oauth_status(
    db: Session = Depends(get_db)
):
    """
    Get OAuth status for all tenants.
    
    Useful for admin debugging.
    
    Returns:
        List of all tenants with their OAuth status
    """
    tenants = db.query(Tenant).all()
    
    return {
        "total_tenants": len(tenants),
        "tenants": [
            {
                "tenant_id": t.id,
                "subdomain": t.zendesk_subdomain,
                "status": t.installation_status,
                "has_oauth": bool(t.oauth_access_token),
                "token_expires_at": t.oauth_token_expires_at.isoformat() if t.oauth_token_expires_at else None
            }
            for t in tenants
        ]
    }
