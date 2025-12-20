"""
API routes for tenant configuration management.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.db.models import Tenant
from api.services.config_service import ConfigService
from api.schemas.config import (
    JiraConfigRequest, JiraConfigResponse,
    SlackConfigRequest, SlackConfigResponse,
    RedactionConfigRequest, RedactionConfigResponse,
    TenantConfigResponse,
    ConnectionTestRequest, ConnectionTestResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()


# Temporary: Get tenant by ID for testing
# TODO: Replace with proper tenant resolution from middleware
async def get_tenant_by_id(tenant_id: int, db: Session = Depends(get_db)) -> Tenant:
    """Get tenant by ID (temporary until OAuth/middleware is ready)."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


# Complete Configuration

@router.get("/tenants/{tenant_id", response_model=TenantConfigResponse)
async def get_tenant_config(
    tenant_id: int,
    db: Session = Depends(get_db)
):
    """Get complete configuration for a tenant."""
    # Verify tenant exists
    await get_tenant_by_id(tenant_id, db)
    
    service = ConfigService(db)
    return service.get_complete_config(tenant_id)


# Jira Configuration

@router.get("/tenants/{tenant_id}/jira", response_model=JiraConfigResponse)
async def get_jira_config(
    tenant_id: int,
    db: Session = Depends(get_db)
):
    """Get Jira configuration."""
    await get_tenant_by_id(tenant_id, db)
    
    service = ConfigService(db)
    config = service.get_jira_config(tenant_id)
    
    if not config:
        raise HTTPException(status_code=404, detail="Jira not configured")
    
    return config


@router.put("/tenants/{tenant_id}/jira", response_model=JiraConfigResponse)
async def set_jira_config(
    tenant_id: int,
    request: JiraConfigRequest,
    db: Session = Depends(get_db)
):
    """Set Jira configuration."""
    await get_tenant_by_id(tenant_id, db)
    
    service = ConfigService(db)
    return service.set_jira_config(tenant_id, request)


# Slack Configuration

@router.get("/tenants/{tenant_id}/slack", response_model=SlackConfigResponse)
async def get_slack_config(
    tenant_id: int,
    db: Session = Depends(get_db)
):
    """Get Slack configuration."""
    await get_tenant_by_id(tenant_id, db)
    
    service = ConfigService(db)
    config = service.get_slack_config(tenant_id)
    
    if not config:
        raise HTTPException(status_code=404, detail="Slack not configured")
    
    return config


@router.put("/tenants/{tenant_id}/slack", response_model=SlackConfigResponse)
async def set_slack_config(
    tenant_id: int,
    request: SlackConfigRequest,
    db: Session = Depends(get_db)
):
    """Set Slack configuration."""
    await get_tenant_by_id(tenant_id, db)
    
    service = ConfigService(db)
    return service.set_slack_config(tenant_id, request)


# Redaction Configuration

@router.get("/tenants/{tenant_id}/redaction", response_model=RedactionConfigResponse)
async def get_redaction_config(
    tenant_id: int,
    db: Session = Depends(get_db)
):
    """Get redaction configuration."""
    await get_tenant_by_id(tenant_id, db)
    
    service = ConfigService(db)
    return service.get_redaction_config(tenant_id)


@router.put("/tenants/{tenant_id}/redaction", response_model=RedactionConfigResponse)
async def set_redaction_config(
    tenant_id: int,
    request: RedactionConfigRequest,
    db: Session = Depends(get_db)
):
    """Set redaction configuration."""
    await get_tenant_by_id(tenant_id, db)
    
    service = ConfigService(db)
    return service.set_redaction_config(tenant_id, request)


# Connection Testing

@router.post("/tenants/{tenant_id}/test-connection", response_model=ConnectionTestResponse)
async def test_connection(
    tenant_id: int,
    request: ConnectionTestRequest,
    db: Session = Depends(get_db)
):
    """Test connection to Jira or Slack."""
    await get_tenant_by_id(tenant_id, db)
    
    service = ConfigService(db)
    
    if request.service == "jira":
        return await test_jira_connection(tenant_id, service)
    elif request.service == "slack":
        return await test_slack_connection(tenant_id, service)
    else:
        raise HTTPException(status_code=400, detail="Invalid service. Use 'jira' or 'slack'")


async def test_jira_connection(tenant_id: int, service: ConfigService) -> ConnectionTestResponse:
    """Test Jira API connection."""
    try:
        # Get Jira config
        jira_config = service.get_jira_config(tenant_id)
        if not jira_config or not jira_config.api_token_set:
            return ConnectionTestResponse(
                success=False,
                message="Jira not configured. Please set up Jira credentials first."
            )
        
        # Get decrypted credentials
        config = service.get_or_create_config(tenant_id)
        jira = config.jira_config
        
        server_url = jira.get("server_url")
        email = jira.get("email")
        api_token = service.get_decrypted_jira_token(tenant_id)
        
        # Test connection using Jira service
        from api.services.integrations.jira import create_jira_client
        
        jira_client = create_jira_client(
            server=server_url,
            email=email,
            api_token=api_token
        )
        
        # Try to get server info
        info = jira_client.jira.server_info()
        
        # Update config with success status
        jira["connection_status"] = "connected"
        jira["last_tested"] = datetime.utcnow().isoformat()
        service.db.commit()
        
        return ConnectionTestResponse(
            success=True,
            message=f"Successfully connected to Jira: {info.get('serverTitle', 'Unknown')}",
            details={
                "server_title": info.get("serverTitle"),
                "version": info.get("version"),
                "build": info.get("buildNumber")
            }
        )
        
    except Exception as e:
        logger.error(f"Jira connection test failed: {e}")
        
        # Update config with failure status
        config = service.get_or_create_config(tenant_id)
        if config.jira_config:
            config.jira_config["connection_status"] = "failed"
            config.jira_config["last_tested"] = datetime.utcnow().isoformat()
            service.db.commit()
        
        return ConnectionTestResponse(
            success=False,
            message=f"Jira connection failed: {str(e)}"
        )


async def test_slack_connection(tenant_id: int, service: ConfigService) -> ConnectionTestResponse:
    """Test Slack webhook."""
    try:
        # Get Slack config
        slack_config = service.get_slack_config(tenant_id)
        if not slack_config or not slack_config.webhook_url_set:
            return ConnectionTestResponse(
                success=False,
                message="Slack not configured. Please set up Slack webhook first."
            )
        
        # Get decrypted webhook
        webhook_url = service.get_decrypted_slack_webhook(tenant_id)
        
        # Send test message
        from api.services.integrations.slack import create_slack_client
        
        slack = create_slack_client(webhook_url)
        slack.send_message({
            "text": "🔔 EscalateSafe Connection Test",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Connection Test Successful!* ✅\n\nYour Slack integration is configured correctly."
                    }
                }
            ]
        })
        
        # Update config with success status
        config = service.get_or_create_config(tenant_id)
        config.slack_config["connection_status"] = "connected"
        config.slack_config["last_tested"] = datetime.utcnow().isoformat()
        service.db.commit()
        
        return ConnectionTestResponse(
            success=True,
            message="Successfully sent test message to Slack"
        )
        
    except Exception as e:
        logger.error(f"Slack connection test failed: {e}")
        
        # Update config with failure status
        config = service.get_or_create_config(tenant_id)
        if config.slack_config:
            config.slack_config["connection_status"] = "failed"
            config.slack_config["last_tested"] = datetime.utcnow().isoformat()
            service.db.commit()
        
        return ConnectionTestResponse(
            success=False,
            message=f"Slack connection failed: {str(e)}"
        )
