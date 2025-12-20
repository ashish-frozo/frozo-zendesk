"""
Configuration schemas for tenant settings.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from enum import Enum


class IssueType(str, Enum):
    """Jira issue types."""
    BUG = "Bug"
    TASK = "Task"
    STORY = "Story"
    EPIC = "Epic"


class Priority(str, Enum):
    """Jira priority levels."""
    HIGHEST = "Highest"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    LOWEST = "Lowest"


class JiraConfigRequest(BaseModel):
    """Jira configuration request."""
    server_url: str = Field(..., description="Jira server URL (e.g., https://company.atlassian.net)")
    email: str = Field(..., description="Jira user email")
    api_token: str = Field(..., description="Jira API token")
    project_key: str = Field(..., description="Default Jira project key (e.g., SCRUM)")
    issue_type: IssueType = Field(default=IssueType.TASK, description="Default issue type")
    priority: Priority = Field(default=Priority.HIGH, description="Default priority")
    labels: List[str] = Field(default=["support-escalation", "escalatesafe"], description="Default labels")
    
    @validator('server_url')
    def validate_server_url(cls, v):
        """Ensure server URL is HTTPS."""
        if not v.startswith('https://'):
            raise ValueError('Server URL must use HTTPS')
        return v.rstrip('/')
    
    @validator('project_key')
    def validate_project_key(cls, v):
        """Ensure project key is uppercase and alphanumeric."""
        if not v.isupper() or not v.isalnum():
            raise ValueError('Project key must be uppercase alphanumeric')
        return v


class JiraConfigResponse(BaseModel):
    """Jira configuration response (without sensitive data)."""
    server_url: str
    email: str
    api_token_set: bool  # Don't expose actual token
    project_key: str
    issue_type: str
    priority: str
    labels: List[str]
    connection_status: Optional[str] = None
    last_tested: Optional[str] = None


class SlackConfigRequest(BaseModel):
    """Slack configuration request."""
    webhook_url: str = Field(..., description="Slack incoming webhook URL")
    channel: Optional[str] = Field(None, description="Channel name (optional, for display)")
    enabled: bool = Field(default=True, description="Enable Slack notifications")
    
    @validator('webhook_url')
    def validate_webhook_url(cls, v):
        """Ensure webhook URL is valid."""
        if not v.startswith('https://hooks.slack.com/services/'):
            raise ValueError('Invalid Slack webhook URL format')
        return v


class SlackConfigResponse(BaseModel):
    """Slack configuration response."""
    webhook_url_set: bool
    channel: Optional[str]
    enabled: bool
    connection_status: Optional[str] = None
    last_tested: Optional[str] = None


class RedactionConfigRequest(BaseModel):
    """Redaction settings request."""
    confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for PII detection (0.0-1.0)"
    )
    enable_indian_entities: bool = Field(
        default=False,
        description="Enable India-specific PII detection (Aadhaar, PAN, etc.)"
    )
    enabled_entity_types: List[str] = Field(
        default=[
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "CREDIT_CARD",
            "PERSON",
            "LOCATION",
            "API_KEY"
        ],
        description="Entity types to detect and redact"
    )
    allow_internal_notes: bool = Field(
        default=False,
        description="Allow including internal notes in escalations"
    )


class RedactionConfigResponse(BaseModel):
    """Redaction settings response."""
    confidence_threshold: float
    enable_indian_entities: bool
    enabled_entity_types: List[str]
    allow_internal_notes: bool


class TenantConfigResponse(BaseModel):
    """Complete tenant configuration."""
    jira: Optional[JiraConfigResponse] = None
    slack: Optional[SlackConfigResponse] = None
    redaction: RedactionConfigResponse


class ConnectionTestRequest(BaseModel):
    """Connection test request."""
    service: str = Field(..., description="Service to test: 'jira' or 'slack'")


class ConnectionTestResponse(BaseModel):
    """Connection test result."""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
