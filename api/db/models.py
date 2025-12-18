"""
Database models for EscalateSafe.

Implements:
- Tenant isolation
- Run tracking with status machine
- Asset storage references
- Export tracking (Jira/Slack)
- Audit trail
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, 
    Boolean, JSON, Numeric, CheckConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class RunStatus(str, Enum):
    """Run lifecycle states."""
    PENDING = "pending"
    PROCESSING = "processing"
    READY_FOR_REVIEW = "ready_for_review"
    EXPORTING = "exporting"
    EXPORTED = "exported"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AssetType(str, Enum):
    """Types of sanitized assets."""
    REDACTED_TEXT = "redacted_text"
    REDACTED_IMAGE = "redacted_image"
    REDACTED_PDF = "redacted_pdf"


class AssetStatus(str, Enum):
    """Asset processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"  # Cannot safely sanitize


class Tenant(Base):
    """Tenant (Zendesk organization) model."""
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    zendesk_subdomain = Column(String(255), unique=True, nullable=False, index=True)
    zendesk_installation_id = Column(String(255), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # Relationships
    users = relationship("TenantUser", back_populates="tenant", cascade="all, delete-orphan")
    config = relationship("TenantConfig", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="tenant", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="tenant", cascade="all, delete-orphan")


class TenantUser(Base):
    """User-tenant association with role."""
    __tablename__ = "tenant_users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    zendesk_user_id = Column(String(255), nullable=False)
    role = Column(String(50), default="agent", nullable=False)  # agent, admin
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    
    __table_args__ = (
        Index("idx_tenant_zendesk_user", "tenant_id", "zendesk_user_id", unique=True),
    )


class TenantConfig(Base):
    """Tenant configuration (JSON blobs)."""
    __tablename__ = "tenant_config"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # JSON configs
    redaction_config = Column(JSON, nullable=False, default={})
    jira_config = Column(JSON, nullable=False, default={})
    slack_config = Column(JSON, nullable=False, default={})
    llm_config = Column(JSON, nullable=False, default={})
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="config")


class Run(Base):
    """Escalation run tracking."""
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    ticket_id = Column(String(255), nullable=False, index=True)
    
    status = Column(String(50), nullable=False, default=RunStatus.PENDING, index=True)
    
    # Options used for this run (for idempotency)
    options_json = Column(JSON, nullable=False, default={})
    
    # Hash of (ticket_id + options + sanitized content) for idempotency
    run_hash = Column(String(64), nullable=True, index=True)
    
    # User tracking
    created_by_user_id = Column(Integer, ForeignKey("tenant_users.id", ondelete="SET NULL"), nullable=True)
    approved_by_user_id = Column(Integer, ForeignKey("tenant_users.id", ondelete="SET NULL"), nullable=True)
    
    # Redaction report (counts, warnings)
    redaction_report = Column(JSON, nullable=True)
    
    # LLM pack (structured bug report)
    llm_pack = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="runs")
    assets = relationship("RunAsset", back_populates="run", cascade="all, delete-orphan")
    exports = relationship("Export", back_populates="run", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_tenant_ticket", "tenant_id", "ticket_id"),
    )


class RunAsset(Base):
    """Sanitized assets (images, PDFs, text exports)."""
    __tablename__ = "run_assets"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    asset_type = Column(String(50), nullable=False)  # AssetType enum
    filename = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=True)
    
    status = Column(String(50), nullable=False, default=AssetStatus.PENDING)
    
    # S3 storage reference (key path)
    storage_ref = Column(String(1000), nullable=True)
    
    # Checksum for integrity
    checksum = Column(String(64), nullable=True)
    
    # Metadata (OCR results, redaction counts, error messages)
    meta_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # Relationships
    run = relationship("Run", back_populates="assets")


class Export(Base):
    """Export tracking for Jira/Slack."""
    __tablename__ = "exports"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Jira
    jira_issue_key = Column(String(100), nullable=True, index=True)
    jira_issue_url = Column(String(500), nullable=True)
    
    # Slack
    slack_message_ts = Column(String(100), nullable=True)
    slack_channel_id = Column(String(100), nullable=True)
    
    status = Column(String(50), nullable=False, default="pending")
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    run = relationship("Run", back_populates="exports")


class AuditEvent(Base):
    """Audit trail."""
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(Integer, ForeignKey("runs.id", ondelete="CASCADE"), nullable=True, index=True)
    
    event_type = Column(String(100), nullable=False, index=True)
    
    # Metadata (no PII, counts only)
    meta_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="audit_events")
