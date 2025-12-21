"""
Helper function to get Zendesk client with OAuth token management.

This should be imported and used by routes instead of creating ZendeskService directly.
"""

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from api.db.models import Tenant
    from sqlalchemy.orm import Session

import logging
logger = logging.getLogger(__name__)


def get_zendesk_client_for_tenant(tenant: 'Tenant', db: 'Session'):
    """
    Get Zendesk client with valid OAuth token for tenant.
    
    This is the primary way to get a Zendesk client for making API calls.
    Automatically handles:
    - Fetching tenant's OAuth token
    - Refreshing expired tokens
    - Falling back to API token if OAuth not configured
    
    Args:
        tenant: Tenant model instance
        db: Database session (for token refresh if needed)
        
    Returns:
        ZendeskService instance ready to use
        
    Example:
        >>> from api.db.models import Tenant
        >>> from api.services.integrations.zendesk_oauth import get_zendesk_client_for_tenant
        >>> tenant = db.query(Tenant).filter_by(subdomain="customer").first()
        >>> zendesk = get_zendesk_client_for_tenant(tenant, db)
        >>> ticket = zendesk.get_ticket(123)
    """
    from api.services.oauth_service import ZendeskOAuthService
    from api.services.integrations.zendesk import ZendeskService
    
    # Try to get OAuth token first
    oauth_service = ZendeskOAuthService(db)
    
    try:
        access_token = oauth_service.get_valid_access_token(tenant)
        logger.info(f"Using OAuth for tenant {tenant.id} ({tenant.zendesk_subdomain})")
        # Create Zendesk service with OAuth token
        return ZendeskService(
            subdomain=tenant.zendesk_subdomain,
            access_token=access_token
        )
    except ValueError as e:
        # OAuth not configured - fall back to API token
        logger.warning(
            f"OAuth not configured for tenant {tenant.id} ({tenant.zendesk_subdomain}). "
            f"Falling back to environment variable credentials. Error: {e}"
        )
        # Create Zendesk service without OAuth (will use env vars)
        return ZendeskService(
            subdomain=tenant.zendesk_subdomain,
            access_token=None  # Will trigger fallback to API token in ZendeskService
        )
