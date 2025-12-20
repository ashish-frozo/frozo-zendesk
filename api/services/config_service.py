"""
Configuration service for managing tenant settings.
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from api.db.models import Tenant, TenantConfig
from api.schemas.config import (
    JiraConfigRequest, JiraConfigResponse,
    SlackConfigRequest, SlackConfigResponse,
    RedactionConfigRequest, RedactionConfigResponse,
    TenantConfigResponse
)
from api.utils.encryption import encrypt_value, decrypt_value

logger = logging.getLogger(__name__)


class ConfigService:
    """Service for managing tenant configuration."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_config(self, tenant_id: int) -> TenantConfig:
        """Get existing config or create default."""
        config = self.db.query(TenantConfig).filter(
            TenantConfig.tenant_id == tenant_id
        ).first()
        
        if not config:
            config = TenantConfig(
                tenant_id=tenant_id,
                redaction_config={
                    "confidence_threshold": 0.5,
                    "enable_indian_entities": False,
                    "enabled_entity_types": [
                        "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD",
                        "PERSON", "LOCATION", "API_KEY"
                    ],
                    "allow_internal_notes": False
                },
                jira_config={},
                slack_config={},
                llm_config={}
            )
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
            logger.info(f"Created default config for tenant {tenant_id}")
        
        return config
    
    # Jira Configuration
    
    def get_jira_config(self, tenant_id: int) -> Optional[JiraConfigResponse]:
        """Get Jira configuration."""
        config = self.get_or_create_config(tenant_id)
        
        if not config.jira_config:
            return None
        
        jira = config.jira_config
        
        return JiraConfigResponse(
            server_url=jira.get("server_url", ""),
            email=jira.get("email", ""),
            api_token_set=bool(jira.get("api_token_encrypted")),
            project_key=jira.get("project_key", ""),
            issue_type=jira.get("issue_type", "Task"),
            priority=jira.get("priority", "High"),
            labels=jira.get("labels", ["support-escalation", "escalatesafe"]),
            connection_status=jira.get("connection_status"),
            last_tested=jira.get("last_tested")
        )
    
    def set_jira_config(self, tenant_id: int, request: JiraConfigRequest) -> JiraConfigResponse:
        """Set Jira configuration."""
        config = self.get_or_create_config(tenant_id)
        
        # Encrypt API token
        encrypted_token = encrypt_value(request.api_token)
        
        config.jira_config = {
            "server_url": request.server_url,
            "email": request.email,
            "api_token_encrypted": encrypted_token,
            "project_key": request.project_key,
            "issue_type": request.issue_type.value,
            "priority": request.priority.value,
            "labels": request.labels,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        self.db.commit()
        logger.info(f"Updated Jira config for tenant {tenant_id}")
        
        return self.get_jira_config(tenant_id)
    
    def get_decrypted_jira_token(self, tenant_id: int) -> Optional[str]:
        """Get decrypted Jira API token for making API calls."""
        config = self.get_or_create_config(tenant_id)
        
        if not config.jira_config:
            return None
        
        encrypted_token = config.jira_config.get("api_token_encrypted")
        if not encrypted_token:
            return None
        
        return decrypt_value(encrypted_token)
    
    # Slack Configuration
    
    def get_slack_config(self, tenant_id: int) -> Optional[SlackConfigResponse]:
        """Get Slack configuration."""
        config = self.get_or_create_config(tenant_id)
        
        if not config.slack_config:
            return None
        
        slack = config.slack_config
        
        return SlackConfigResponse(
            webhook_url_set=bool(slack.get("webhook_url_encrypted")),
            channel=slack.get("channel"),
            enabled=slack.get("enabled", True),
            connection_status=slack.get("connection_status"),
            last_tested=slack.get("last_tested")
        )
    
    def set_slack_config(self, tenant_id: int, request: SlackConfigRequest) -> SlackConfigResponse:
        """Set Slack configuration."""
        config = self.get_or_create_config(tenant_id)
        
        # Encrypt webhook URL
        encrypted_webhook = encrypt_value(request.webhook_url)
        
        config.slack_config = {
            "webhook_url_encrypted": encrypted_webhook,
            "channel": request.channel,
            "enabled": request.enabled,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        self.db.commit()
        logger.info(f"Updated Slack config for tenant {tenant_id}")
        
        return self.get_slack_config(tenant_id)
    
    def get_decrypted_slack_webhook(self, tenant_id: int) -> Optional[str]:
        """Get decrypted Slack webhook URL for making API calls."""
        config = self.get_or_create_config(tenant_id)
        
        if not config.slack_config:
            return None
        
        encrypted_webhook = config.slack_config.get("webhook_url_encrypted")
        if not encrypted_webhook:
            return None
        
        return decrypt_value(encrypted_webhook)
    
    # Redaction Configuration
    
    def get_redaction_config(self, tenant_id: int) -> RedactionConfigResponse:
        """Get redaction configuration."""
        config = self.get_or_create_config(tenant_id)
        
        redaction = config.redaction_config or {}
        
        return RedactionConfigResponse(
            confidence_threshold=redaction.get("confidence_threshold", 0.5),
            enable_indian_entities=redaction.get("enable_indian_entities", False),
            enabled_entity_types=redaction.get("enabled_entity_types", [
                "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD",
                "PERSON", "LOCATION", "API_KEY"
            ]),
            allow_internal_notes=redaction.get("allow_internal_notes", False)
        )
    
    def set_redaction_config(self, tenant_id: int, request: RedactionConfigRequest) -> RedactionConfigResponse:
        """Set redaction configuration."""
        config = self.get_or_create_config(tenant_id)
        
        config.redaction_config = {
            "confidence_threshold": request.confidence_threshold,
            "enable_indian_entities": request.enable_indian_entities,
            "enabled_entity_types": request.enabled_entity_types,
            "allow_internal_notes": request.allow_internal_notes,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        self.db.commit()
        logger.info(f"Updated redaction config for tenant {tenant_id}")
        
        return self.get_redaction_config(tenant_id)
    
    # Complete Configuration
    
    def get_complete_config(self, tenant_id: int) -> TenantConfigResponse:
        """Get all configuration for a tenant."""
        return TenantConfigResponse(
            jira=self.get_jira_config(tenant_id),
            slack=self.get_slack_config(tenant_id),
            redaction=self.get_redaction_config(tenant_id)
        )
