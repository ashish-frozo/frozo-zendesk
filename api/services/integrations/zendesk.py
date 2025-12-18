"""
Zendesk API integration service.

Handles:
- OAuth authentication
- Ticket fetching
- Comment retrieval (public + internal notes based on tenant config)
- Attachment downloading
"""

import logging
from typing import Dict, List, Optional, Any
from zenpy import Zenpy
from zenpy.lib.api_objects import Ticket, Comment
import os
from api.config import settings

logger = logging.getLogger(__name__)


class ZendeskService:
    """Service for interacting with Zendesk API."""
    
    def __init__(self, subdomain: str, access_token: Optional[str] = None):
        """
        Initialize Zendesk client.
        
        Args:
            subdomain: Zendesk subdomain (e.g., 'mycompany')
            access_token: OAuth access token (if available)
        """
        self.subdomain = subdomain
        
        # For now, using OAuth token. In production, implement full OAuth flow
        if access_token:
            self.client = Zenpy(
                subdomain=subdomain,
                oauth_token=access_token
            )
        else:
            # Fallback to API token for development
            # In production, this should be removed and OAuth enforced
            logger.warning("Using API token authentication - should use OAuth in production")
            # This requires you to set ZENDESK_EMAIL and ZENDESK_API_TOKEN in .env
            email = os.getenv("ZENDESK_EMAIL")
            token = os.getenv("ZENDESK_API_TOKEN")
            if email and token:
                self.client = Zenpy(
                    subdomain=subdomain,
                    email=email,
                    token=token
                )
            else:
                raise ValueError("No Zendesk credentials provided")
    
    def get_ticket(self, ticket_id: int) -> Dict[str, Any]:
        """
        Fetch ticket details.
        
        Args:
            ticket_id: Zendesk ticket ID
            
        Returns:
            Ticket data as dictionary with fields:
            - id, subject, description, status, priority, created_at
            - requester: {id, name, email}
            - channel: source channel (web, email, chat, etc.)
        """
        try:
            ticket = self.client.tickets(id=ticket_id)
            
            # Get requester details
            requester = self.client.users(id=ticket.requester_id)
            
            return {
                "id": ticket.id,
                "subject": ticket.subject,
                "description": ticket.description or "",
                "status": ticket.status,
                "priority": ticket.priority,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
                "requester": {
                    "id": requester.id,
                    "name": requester.name,
                    "email": requester.email
                },
                "channel": ticket.via.channel if hasattr(ticket, 'via') else "unknown",
                "tags": ticket.tags if ticket.tags else []
            }
        except Exception as e:
            logger.error(f"Failed to fetch ticket {ticket_id}: {e}")
            raise
    
    def get_comments(
        self, 
        ticket_id: int, 
        include_internal: bool = False,
        last_n_public: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Fetch ticket comments.
        
        Args:
            ticket_id: Zendesk ticket ID
            include_internal: Whether to include internal notes (requires tenant opt-in)
            last_n_public: Number of most recent public comments to include
            
        Returns:
            List of comment dictionaries with:
            - id, body, public, created_at, author_id
        """
        try:
            ticket = self.client.tickets(id=ticket_id)
            comments = []
            
            # Get all comments
            all_comments = list(self.client.tickets.comments(ticket=ticket))
            
            # Filter and limit
            public_comments = [c for c in all_comments if c.public]
            internal_comments = [c for c in all_comments if not c.public]
            
            # Get last N public comments (most recent first)
            selected_public = public_comments[-last_n_public:] if last_n_public > 0 else []
            
            # Build result
            for comment in selected_public:
                comments.append({
                    "id": comment.id,
                    "body": comment.body or "",
                    "public": True,
                    "created_at": comment.created_at.isoformat() if comment.created_at else None,
                    "author_id": comment.author_id
                })
            
            # Add internal notes if allowed
            if include_internal:
                for comment in internal_comments:
                    comments.append({
                        "id": comment.id,
                        "body": comment.body or "",
                        "public": False,
                        "created_at": comment.created_at.isoformat() if comment.created_at else None,
                        "author_id": comment.author_id
                    })
            
            return comments
            
        except Exception as e:
            logger.error(f"Failed to fetch comments for ticket {ticket_id}: {e}")
            raise
    
    def get_attachments(self, ticket_id: int) -> List[Dict[str, Any]]:
        """
        Get attachment metadata from ticket and comments.
        
        Args:
            ticket_id: Zendesk ticket ID
            
        Returns:
            List of attachment dictionaries with:
            - id, filename, content_url, content_type, size
        """
        try:
            ticket = self.client.tickets(id=ticket_id)
            attachments = []
            
            # Get comments with attachments
            for comment in self.client.tickets.comments(ticket=ticket):
                if hasattr(comment, 'attachments') and comment.attachments:
                    for attachment in comment.attachments:
                        attachments.append({
                            "id": attachment.id,
                            "filename": attachment.file_name,
                            "content_url": attachment.content_url,
                            "content_type": attachment.content_type,
                            "size": attachment.size
                        })
            
            return attachments
            
        except Exception as e:
            logger.error(f"Failed to fetch attachments for ticket {ticket_id}: {e}")
            raise
    
    def download_attachment(self, content_url: str) -> bytes:
        """
        Download attachment content.
        
        Args:
            content_url: Zendesk attachment URL
            
        Returns:
            Attachment content as bytes
        """
        try:
            import requests
            response = requests.get(content_url, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Failed to download attachment from {content_url}: {e}")
            raise


def get_zendesk_client(subdomain: str, access_token: Optional[str] = None) -> ZendeskService:
    """Factory function to create Zendesk service instance."""
    return ZendeskService(subdomain=subdomain, access_token=access_token)
