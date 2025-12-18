"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class RunCreateRequest(BaseModel):
    """Request to create a new run."""
    ticket_id: str = Field(..., description="Zendesk ticket ID")
    include_internal_notes: bool = Field(default=False, description="Include internal notes (requires tenant opt-in)")
    include_last_public_comments: int = Field(default=1, ge=0, le=10, description="Number of recent public comments to include")


class RedactionReportResponse(BaseModel):
    """Redaction report details."""
    total_detections: int
    entity_counts: Dict[str, int]
    low_confidence_count: int
    low_confidence_warnings: List[Dict[str, Any]]


class RunStatusResponse(BaseModel):
    """Run status response."""
    id: int
    ticket_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    redaction_report: Optional[RedactionReportResponse] = None
    preview_available: bool = Field(default=False)


class RunCreateResponse(BaseModel):
    """Response after creating a run."""
    run_id: int
    status: str
    message: str


class PreviewTextResponse(BaseModel):
    """Sanitized text preview."""
    redacted_text: str
    diff_segments: List[Dict[str, Any]]
    redaction_summary: Dict[str, Any]


class ApproveRequest(BaseModel):
    """Request to approve and export a run."""
    jira: Dict[str, Any] = Field(..., description="Jira configuration for this export")
    slack: Optional[Dict[str, Any]] = Field(default=None, description="Slack configuration")


class ApproveResponse(BaseModel):
    """Response after approving export."""
    run_id: int
    status: str
    message: str
    jira_issue_key: Optional[str] = None
