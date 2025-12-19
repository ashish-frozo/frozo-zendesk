"""
API routes for run management.

Endpoints:
- POST /v1/runs - Create new escalation run
- GET /v1/runs/{run_id} - Get run status
- GET /v1/runs/{run_id}/preview/text - Get sanitized text preview
- POST /v1/runs/{run_id}/approve - Approve and export
- POST /v1/runs/{run_id}/cancel - Cancel run
"""

import logging
import hashlib
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.db.models import Run, RunStatus, Tenant, TenantConfig, AuditEvent, Export
from api.schemas.runs import (
    RunCreateRequest,
    RunCreateResponse,
    RunStatusResponse,
    PreviewTextResponse,
    ApproveRequest,
    ApproveResponse,
    RedactionReportResponse
)
from api.services.redaction import create_detector, create_redactor
from api.services.integrations.zendesk import get_zendesk_client

logger = logging.getLogger(__name__)

router = APIRouter()


# Helper function to get tenant (simplified for now, should use middleware)
def get_current_tenant(db: Session, subdomain: str = "demo") -> Tenant:
    """Get or create tenant by subdomain."""
    tenant = db.query(Tenant).filter(Tenant.zendesk_subdomain == subdomain).first()
    if not tenant:
        # Create demo tenant
        tenant = Tenant(zendesk_subdomain=subdomain)
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        
        # Create default config
        config = TenantConfig(
            tenant_id=tenant.id,
            redaction_config={"enable_indian_entities": False},
            jira_config={},
            slack_config={},
            llm_config={}
        )
        db.add(config)
        db.commit()
    
    return tenant


@router.post("/", response_model=RunCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    request: RunCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new escalation run.
    
    Process:
    1. Validate tenant config (internal notes opt-in)
    2. Fetch ticket from Zendesk
    3. Detect PII in text
    4. Generate redaction report
    5. Store run with status=ready_for_review
    """
    try:
        # Get tenant (simplified - should come from middleware)
        # Use environment variable or default to 'demo'
        from api.config import settings
        actual_subdomain = settings.zendesk_subdomain if hasattr(settings, 'zendesk_subdomain') else "frozoai"
        tenant = get_current_tenant(db, subdomain=actual_subdomain)
        
        # Get tenant config
        config = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant.id).first()
        if not config:
            raise HTTPException(status_code=500, detail="Tenant configuration not found")
        
        # Validate internal notes opt-in
        if request.include_internal_notes:
            redaction_config = config.redaction_config or {}
            if not redaction_config.get("allow_internal_notes", False):
                raise HTTPException(
                    status_code=403,
                    detail="Internal notes not enabled for this tenant. Contact admin to enable."
                )
        
        # Create run record
        run = Run(
            tenant_id=tenant.id,
            ticket_id=request.ticket_id,
            status=RunStatus.PROCESSING,
            options_json={
                "include_internal_notes": request.include_internal_notes,
                "include_last_public_comments": request.include_last_public_comments
            }
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        
        # Log audit event
        audit = AuditEvent(
            tenant_id=tenant.id,
            run_id=run.id,
            event_type="run_created",
            meta_json={"ticket_id": request.ticket_id}
        )
        db.add(audit)
        db.commit()
        
        # Fetch ticket from Zendesk
        try:
            zendesk = get_zendesk_client(subdomain=tenant.zendesk_subdomain)
            ticket_data = zendesk.get_ticket(int(request.ticket_id))
            comments = zendesk.get_comments(
                ticket_id=int(request.ticket_id),
                include_internal=request.include_internal_notes,
                last_n_public=request.include_last_public_comments
            )
            
            # Combine text for PII detection
            text_to_analyze = ticket_data["description"]
            for comment in comments:
                text_to_analyze += "\n\n" + comment["body"]
            
        except Exception as e:
            logger.error(f"Failed to fetch ticket {request.ticket_id}: {e}")
            run.status = RunStatus.FAILED
            db.commit()
            raise HTTPException(status_code=500, detail=f"Failed to fetch ticket: {str(e)}")
        
        # Detect PII
        try:
            redaction_config = config.redaction_config or {}
            detector = create_detector(
                enable_indian_entities=redaction_config.get("enable_indian_entities", False),
                confidence_threshold=redaction_config.get("confidence_threshold", 0.5)
            )
            detection_results = detector.analyze(text_to_analyze)
            detection_report = detector.format_detection_report(detection_results)
            
            # Redact text
            redactor = create_redactor()
            redaction_result = redactor.redact_with_report(text_to_analyze, detection_results)
            
            # Store results
            run.redaction_report = {
                **detection_report,
                **redaction_result
            }
            run.status = RunStatus.READY_FOR_REVIEW
            
            # Generate run hash for idempotency
            hash_input = f"{tenant.id}:{request.ticket_id}:{redaction_result['redacted_text']}"
            run.run_hash = hashlib.sha256(hash_input.encode()).hexdigest()
            
            db.commit()
            
            # Log completion
            audit = AuditEvent(
                tenant_id=tenant.id,
                run_id=run.id,
                event_type="redaction_completed",
                meta_json={
                    "total_detections": detection_report["total_detections"],
                    "entity_counts": detection_report["entity_counts"]
                }
            )
            db.add(audit)
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to process ticket {request.ticket_id}: {e}")
            run.status = RunStatus.FAILED
            db.commit()
            raise HTTPException(status_code=500, detail=f"Failed to process ticket: {str(e)}")
        
        return RunCreateResponse(
            run_id=run.id,
            status=run.status,
            message="Run created successfully. Preview ready for review."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating run: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{run_id}", response_model=RunStatusResponse)
async def get_run_status(
    run_id: int,
    db: Session = Depends(get_db)
):
    """Get run status and redaction report."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    redaction_report = None
    if run.redaction_report:
        redaction_report = RedactionReportResponse(
            total_detections=run.redaction_report.get("total_detections", 0),
            entity_counts=run.redaction_report.get("entity_counts", {}),
            low_confidence_count=run.redaction_report.get("low_confidence_count", 0),
            low_confidence_warnings=run.redaction_report.get("low_confidence_warnings", [])
        )
    
    return RunStatusResponse(
        id=run.id,
        ticket_id=run.ticket_id,
        status=run.status,
        created_at=run.created_at,
        updated_at=run.updated_at,
        redaction_report=redaction_report,
        preview_available=run.status == RunStatus.READY_FOR_REVIEW
    )


@router.get("/{run_id}/preview/text", response_model=PreviewTextResponse)
async def get_text_preview(
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Get sanitized text preview with diff view.
    
    Only available when run status = ready_for_review.
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if run.status != RunStatus.READY_FOR_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Preview not available. Run status: {run.status}"
        )
    
    if not run.redaction_report:
        raise HTTPException(status_code=500, detail="Redaction report not found")
    
    return PreviewTextResponse(
        redacted_text=run.redaction_report.get("redacted_text", ""),
        diff_segments=run.redaction_report.get("diff_segments", []),
        redaction_summary={
            "total_redactions": run.redaction_report.get("total_redactions", 0),
            "entities_redacted": run.redaction_report.get("entities_redacted", {}),
            "original_length": run.redaction_report.get("original_length", 0),
            "redacted_length": run.redaction_report.get("redacted_length", 0)
        }
    )


@router.post("/{run_id}/approve", response_model=ApproveResponse)
async def approve_and_export(
    run_id: int,
    request: ApproveRequest,
    db: Session = Depends(get_db)
):
    """
    Approve run and export to Jira + Slack.
    
    Process:
    1. Check run status = ready_for_review
    2. Enforce idempotency via run_hash
    3. Create Jira issue with sanitized content
    4. Upload sanitized attachments (future)
    5. Post Slack notification
    6. Update run status to exported
    7. Log audit events
    
    Idempotency: Multiple approvals with same run_hash create only one Jira issue.
    """
    from api.services.integrations.jira import create_jira_client, retry_with_backoff
    from api.services.integrations.slack import create_slack_client
    from api.config import settings
    
    try:
        # Get run
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Validate status
        if run.status != RunStatus.READY_FOR_REVIEW:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve run with status: {run.status}"
            )
        
        # Check for existing export (idempotency)
        existing_export = db.query(Export).filter(Export.run_id == run_id).first()
        if existing_export and existing_export.jira_issue_key:
            logger.info(f"Run {run_id} already exported to {existing_export.jira_issue_key}")
            return ApproveResponse(
                run_id=run_id,
                status="exported",
                message=f"Already exported to {existing_export.jira_issue_key}",
                jira_issue_key=existing_export.jira_issue_key
            )
        
        # Update run status
        run.status = RunStatus.EXPORTING
        db.commit()
        
        # Log audit event
        audit = AuditEvent(
            tenant_id=run.tenant_id,
            run_id=run.id,
            event_type="export_started",
            meta_json={"jira_config": request.jira}
        )
        db.add(audit)
        db.commit()
        
        # Get Jira config from request or tenant config
        jira_config = request.jira
        project_key = jira_config.get("project_key", "SUP")
        issue_type = jira_config.get("issue_type", "Bug")
        priority = jira_config.get("priority", "High")
        labels = jira_config.get("labels", ["support-escalation", "escalatesafe"])
        components = jira_config.get("components", [])
        
        # Get sanitized content
        redacted_text = run.redaction_report.get("redacted_text", "")
        summary = jira_config.get("summary", f"Escalation from Zendesk #{run.ticket_id}")[:120]
        
        # Build description
        description = f"""h2. Escalated from Zendesk Ticket #{run.ticket_id}

{redacted_text}

---
_This issue was automatically created by EscalateSafe with PII redaction._
_Total PII entities redacted: {run.redaction_report.get('total_redactions', 0)}_
"""
        
        # Create or get export record
        if not existing_export:
            export_record = Export(
                run_id=run.id,
                status="pending"
            )
            db.add(export_record)
            db.commit()
            db.refresh(export_record)
        else:
            export_record = existing_export
        
        try:
            # Create Jira client
            jira = create_jira_client(
                server=settings.jira_cloud_id or "https://your-domain.atlassian.net",
                email=settings.jira_user_email,
                api_token=settings.jira_api_token
            )
            
            # Create Jira issue with retry
            def create_issue_with_retry():
                return jira.create_issue(
                    project_key=project_key,
                    summary=summary,
                    description=description,
                    issue_type=issue_type,
                    priority=priority,
                    labels=labels,
                    components=components
                )
            
            issue_result = retry_with_backoff(create_issue_with_retry, max_retries=5)
            
            # Update export record
            export_record.jira_issue_key = issue_result["key"]
            export_record.jira_issue_url = issue_result["url"]
            export_record.status = "success"
            db.commit()
            
            # Log success
            audit = AuditEvent(
                tenant_id=run.tenant_id,
                run_id=run.id,
                event_type="export_succeeded",
                meta_json={
                    "jira_issue_key": issue_result["key"],
                    "jira_issue_url": issue_result["url"]
                }
            )
            db.add(audit)
            db.commit()
            
            logger.info(f"Created Jira issue {issue_result['key']} for run {run_id}")
            
            # Post Slack notification (optional, non-blocking)
            if request.slack and request.slack.get("enabled", False):
                try:
                    if settings.slack_webhook_url:
                        slack = create_slack_client(settings.slack_webhook_url)
                        
                        zendesk_url = f"https://{run.tenant.zendesk_subdomain}.zendesk.com/agent/tickets/{run.ticket_id}"
                        
                        slack.post_escalation_notification(
                            jira_issue_key=issue_result["key"],
                            jira_issue_url=issue_result["url"],
                            zendesk_ticket_id=run.ticket_id,
                            zendesk_ticket_url=zendesk_url,
                            summary=summary,
                            severity=priority
                        )
                        
                        # Log Slack success
                        audit = AuditEvent(
                            tenant_id=run.tenant_id,
                            run_id=run.id,
                            event_type="slack_post_succeeded",
                            meta_json={"jira_issue_key": issue_result["key"]}
                        )
                        db.add(audit)
                        db.commit()
                        
                        logger.info(f"Posted Slack notification for {issue_result['key']}")
                    
                except Exception as slack_error:
                    # Log Slack failure but don't block Jira export
                    logger.error(f"Slack notification failed: {slack_error}")
                    audit = AuditEvent(
                        tenant_id=run.tenant_id,
                        run_id=run.id,
                        event_type="slack_post_failed",
                        meta_json={"error": str(slack_error)}
                    )
                    db.add(audit)
                    db.commit()
            
            # Update run status to exported
            run.status = RunStatus.EXPORTED
            db.commit()
            
            return ApproveResponse(
                run_id=run_id,
                status="exported",
                message=f"Successfully exported to Jira: {issue_result['key']}",
                jira_issue_key=issue_result["key"]
            )
            
        except Exception as jira_error:
            # Log Jira export failure
            logger.error(f"Jira export failed for run {run_id}: {jira_error}")
            
            export_record.status = "failed"
            export_record.error_code = "JIRA_API_ERROR"
            export_record.error_message = str(jira_error)[:500]
            db.commit()
            
            audit = AuditEvent(
                tenant_id=run.tenant_id,
                run_id=run.id,
                event_type="export_failed",
                meta_json={
                    "error": str(jira_error)[:200],
                    "error_code": "JIRA_API_ERROR"
                }
            )
            db.add(audit)
            db.commit()
            
            run.status = RunStatus.FAILED
            db.commit()
            
            raise HTTPException(
                status_code=500,
                detail=f"Failed to export to Jira: {str(jira_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during export: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{run_id}/cancel")
async def cancel_run(
    run_id: int,
    db: Session = Depends(get_db)
):
    """Cancel a run. No exports will occur."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if run.status in [RunStatus.EXPORTED, RunStatus.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel run with status: {run.status}"
        )
    
    run.status = RunStatus.CANCELLED
    db.commit()
    
    # Log audit event
    audit = AuditEvent(
        tenant_id=run.tenant_id,
        run_id=run.id,
        event_type="run_cancelled",
        meta_json={}
    )
    db.add(audit)
    db.commit()
    
    return {"message": "Run cancelled successfully", "run_id": run_id}
