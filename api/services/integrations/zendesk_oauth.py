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
    - Raising errors if OAuth not configured
    
    Args:
        tenant: Tenant model instance
        db: Database session (for token refresh if needed)
        
    Returns:
        ZendeskService instance ready to use
        
    Raises:
        ValueError: If tenant doesn't have OAuth configured
        
    Example:
        >>> from api.db.models import Tenant
        >>> from api.services.integrations.zendesk_oauth import get_zendesk_client_for_tenant
        >>> tenant = db.query(Tenant).filter_by(subdomain="customer").first()
        >>> zendesk = get_zendesk_client_for_tenant(tenant, db)
        >>> ticket = zendesk.get_ticket(123)
    """
    from api.services.oauth_service import ZendeskOAuthService
    from api.services.integrations.zendesk import ZendeskService
    
    # Get valid access token (auto-refreshes if expired)
    oauth_service = ZendeskOAuthService(db)
    
    try:
        access_token = oauth_service.get_valid_access_token(tenant)
    except ValueError as e:
        logger.error(f"Failed to get OAuth token for tenant {tenant.id}: {e}")
        raise ValueError(
            f"OAuth not configured for {tenant.zendesk_subdomain}. "
            f"User must reinstall the app to grant permissions."
        )
    
    # Create Zendesk service with OAuth token
    return ZendeskService(
        subdomain=tenant.zendesk_subdomain,
        access_token=access_token
    )
