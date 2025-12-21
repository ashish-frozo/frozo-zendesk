"""
Zendesk OAuth service for token management and multi-tenant authentication.

Handles:
- OAuth authorization code exchange
- Access token refresh
- Token validation and expiry management
- Per-tenant token storage
"""

from datetime import datetime, timedelta
import requests
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session

from api.db.models import Tenant
from api.config import settings

logger = logging.getLogger(__name__)


class ZendeskOAuthService:
    """Manages Zendesk OAuth flow and token lifecycle for multi-tenant support."""
    
    def __init__(self, db: Session):
        """
        Initialize OAuth service.
        
        Args:
            db: Database session for tenant operations
        """
        self.db = db
    
    def exchange_code_for_tokens(
        self, 
        code: str, 
        subdomain: str,
        redirect_uri: str
    ) -> Dict[str, any]:
        """
        Exchange authorization code for access & refresh tokens.
        
        This is called after user approves OAuth consent screen.
        
        Args:
            code: Authorization code from Zendesk
            subdomain: Zendesk subdomain (e.g., 'frozoai')
            redirect_uri: OAuth callback URL that was registered
            
        Returns:
            Dict with access_token, refresh_token, expires_in, scope
            
        Raises:
            ValueError: If token exchange fails
        """
        token_url = f"https://{subdomain}.zendesk.com/oauth/tokens"
        
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.zendesk_client_id,
            "client_secret": settings.zendesk_client_secret,
            "redirect_uri": redirect_uri,
            "scope": "read write"
        }
        
        try:
            logger.info(f"Exchanging OAuth code for tokens for subdomain: {subdomain}")
            response = requests.post(token_url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"OAuth tokens obtained successfully for {subdomain}")
            
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in", 7200),  # Default 2 hours
                "scope": data.get("scope", "read write")
            }
            
        except requests.RequestException as e:
            logger.error(f"Failed to exchange OAuth code for {subdomain}: {e}")
            raise ValueError(f"OAuth token exchange failed: {str(e)}")
    
    def refresh_access_token(self, tenant: Tenant) -> str:
        """
        Refresh expired access token using refresh token.
        
        Automatically called when access token is expired or about to expire.
        
        Args:
            tenant: Tenant with refresh_token
            
        Returns:
            New access token
            
        Raises:
            ValueError: If refresh fails or tenant has no refresh token
        """
        if not tenant.oauth_refresh_token:
            raise ValueError(f"No refresh token available for tenant {tenant.id}")
        
        token_url = f"https://{tenant.zendesk_subdomain}.zendesk.com/oauth/tokens"
        
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": tenant.oauth_refresh_token,
            "client_id": settings.zendesk_client_id,
            "client_secret": settings.zendesk_client_secret
        }
        
        try:
            logger.info(f"Refreshing OAuth token for tenant {tenant.id} ({tenant.zendesk_subdomain})")
            response = requests.post(token_url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Update tenant with new tokens
            tenant.oauth_access_token = data["access_token"]
            tenant.oauth_token_expires_at = datetime.utcnow() + timedelta(
                seconds=data.get("expires_in", 7200)
            )
            
            # Refresh token might be rotated
            if "refresh_token" in data:
                tenant.oauth_refresh_token = data["refresh_token"]
            
            self.db.commit()
            
            logger.info(f"Successfully refreshed OAuth token for tenant {tenant.id}")
            return data["access_token"]
            
        except requests.RequestException as e:
            logger.error(f"Failed to refresh OAuth token for tenant {tenant.id}: {e}")
            raise ValueError(f"OAuth token refresh failed: {str(e)}")
    
    def get_valid_access_token(self, tenant: Tenant) -> str:
        """
        Get valid access token, automatically refreshing if expired.
        
        Call this before making any Zendesk API requests to ensure
        you have a valid token.
        
        Args:
            tenant: Tenant record
            
        Returns:
            Valid access token ready to use
            
        Raises:
            ValueError: If no token available or refresh fails
        """
        # Check if token exists
        if not tenant.oauth_access_token:
            raise ValueError(
                f"No OAuth access token for tenant {tenant.id}. "
                f"User must reinstall the app to grant permissions."
            )
        
        # Check if token is expired or about to expire (within 5 minutes)
        if tenant.oauth_token_expires_at:
            time_until_expiry = tenant.oauth_token_expires_at - datetime.utcnow()
            
            if time_until_expiry.total_seconds() < 300:  # 5 minutes
                logger.info(
                    f"Token for tenant {tenant.id} expires in "
                    f"{time_until_expiry.total_seconds()}s, refreshing..."
                )
                return self.refresh_access_token(tenant)
        
        return tenant.oauth_access_token
    
    def store_tokens(
        self, 
        tenant: Tenant, 
        access_token: str,
        refresh_token: Optional[str],
        expires_in: int,
        scope: str
    ):
        """
        Store OAuth tokens in database for tenant.
        
        Args:
            tenant: Tenant record to update
            access_token: Access token from Zendesk
            refresh_token: Refresh token (optional)
            expires_in: Token lifetime in seconds
            scope: Granted OAuth scopes
        """
        tenant.oauth_access_token = access_token
        tenant.oauth_refresh_token = refresh_token
        tenant.oauth_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        tenant.oauth_scopes = scope
        tenant.installation_status = "active"
        
        self.db.commit()
        logger.info(
            f"Stored OAuth tokens for tenant {tenant.id} ({tenant.zendesk_subdomain}). "
            f"Expires at: {tenant.oauth_token_expires_at}"
        )
    
    def revoke_tokens(self, tenant: Tenant):
        """
        Revoke and clear OAuth tokens for tenant.
        
        Call this when user uninstalls app or revokes access.
        
        Args:
            tenant: Tenant record to clear
        """
        tenant.oauth_access_token = None
        tenant.oauth_refresh_token = None
        tenant.oauth_token_expires_at = None
        tenant.installation_status = "suspended"
        
        self.db.commit()
        logger.info(f"Revoked OAuth tokens for tenant {tenant.id}")
