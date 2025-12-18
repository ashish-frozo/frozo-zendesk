"""
Jira Cloud API integration service.

Handles:
- OAuth/API token authentication
- Issue creation with field mapping
- Attachment uploads
- Error handling and retries
"""

import logging
from typing import Dict, List, Optional, Any
from jira import JIRA, JIRAError
import time

logger = logging.getLogger(__name__)


class JiraService:
    """Service for interacting with Jira Cloud API."""
    
    def __init__(
        self,
        cloud_id: Optional[str] = None,
        server: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
        oauth_dict: Optional[Dict] = None
    ):
        """
        Initialize Jira client.
        
        Args:
            cloud_id: Jira Cloud ID (for cloud instances)
            server: Jira server URL (alternative to cloud_id)
            email: User email (for API token auth)
            api_token: API token (for API token auth)
            oauth_dict: OAuth credentials (alternative to API token)
        """
        # Determine server URL
        if cloud_id:
            self.server = f"https://api.atlassian.com/ex/jira/{cloud_id}"
        elif server:
            self.server = server
        else:
            raise ValueError("Either cloud_id or server must be provided")
        
        # Initialize JIRA client
        try:
            if oauth_dict:
                self.client = JIRA(server=self.server, oauth=oauth_dict)
                logger.info(f"Jira client initialized with OAuth for {self.server}")
            elif email and api_token:
                self.client = JIRA(
                    server=self.server,
                    basic_auth=(email, api_token)
                )
                logger.info(f"Jira client initialized with API token for {self.server}")
            else:
                raise ValueError("Either oauth_dict or (email + api_token) required")
                
        except JIRAError as e:
            logger.error(f"Failed to initialize Jira client: {e}")
            raise
    
    def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Bug",
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
        components: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a Jira issue.
        
        Args:
            project_key: Jira project key (e.g., "SUP")
            summary: Issue summary (title)
            description: Issue description (body)
            issue_type: Issue type (Bug, Task, Story, etc.)
            priority: Priority level (Highest, High, Medium, Low, Lowest)
            labels: List of labels
            components: List of component names
            custom_fields: Additional custom fields
            
        Returns:
            Dictionary with:
            - key: Jira issue key (e.g., "SUP-123")
            - id: Jira issue ID
            - url: Jira issue URL
        """
        try:
            # Build issue fields
            fields = {
                "project": {"key": project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type},
            }
            
            # Add optional fields
            if priority:
                fields["priority"] = {"name": priority}
            
            if labels:
                fields["labels"] = labels
            
            if components:
                fields["components"] = [{"name": c} for c in components]
            
            # Merge custom fields
            if custom_fields:
                fields.update(custom_fields)
            
            # Create issue
            logger.info(f"Creating Jira issue in project {project_key}")
            issue = self.client.create_issue(fields=fields)
            
            issue_url = f"{self.server}/browse/{issue.key}"
            
            logger.info(f"Created Jira issue: {issue.key} ({issue_url})")
            
            return {
                "key": issue.key,
                "id": issue.id,
                "url": issue_url
            }
            
        except JIRAError as e:
            logger.error(f"Failed to create Jira issue: {e}")
            raise
    
    def upload_attachment(
        self,
        issue_key: str,
        filename: str,
        content: bytes
    ) -> Dict[str, Any]:
        """
        Upload attachment to Jira issue.
        
        Args:
            issue_key: Jira issue key (e.g., "SUP-123")
            filename: Attachment filename
            content: File content as bytes
            
        Returns:
            Dictionary with attachment metadata
        """
        try:
            import io
            
            logger.info(f"Uploading attachment '{filename}' to {issue_key}")
            
            # Create file-like object from bytes
            file_obj = io.BytesIO(content)
            file_obj.name = filename
            
            # Upload attachment
            attachment = self.client.add_attachment(
                issue=issue_key,
                attachment=file_obj,
                filename=filename
            )
            
            logger.info(f"Uploaded attachment: {attachment.filename} ({attachment.size} bytes)")
            
            return {
                "id": attachment.id,
                "filename": attachment.filename,
                "size": attachment.size,
                "created": attachment.created
            }
            
        except JIRAError as e:
            logger.error(f"Failed to upload attachment: {e}")
            raise
    
    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """
        Get Jira issue details.
        
        Args:
            issue_key: Jira issue key
            
        Returns:
            Issue details dictionary
        """
        try:
            issue = self.client.issue(issue_key)
            return {
                "key": issue.key,
                "id": issue.id,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
                "url": f"{self.server}/browse/{issue.key}"
            }
        except JIRAError as e:
            logger.error(f"Failed to get Jira issue {issue_key}: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test Jira connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to get server info
            self.client.server_info()
            logger.info("Jira connection test successful")
            return True
        except Exception as e:
            logger.error(f"Jira connection test failed: {e}")
            return False


def create_jira_client(
    cloud_id: Optional[str] = None,
    server: Optional[str] = None,
    email: Optional[str] = None,
    api_token: Optional[str] = None,
    oauth_dict: Optional[Dict] = None
) -> JiraService:
    """Factory function to create Jira service instance."""
    return JiraService(
        cloud_id=cloud_id,
        server=server,
        email=email,
        api_token=api_token,
        oauth_dict=oauth_dict
    )


def retry_with_backoff(func, max_retries: int = 5, initial_delay: float = 1.0):
    """
    Retry function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum retry attempts
        initial_delay: Initial delay in seconds
        
    Returns:
        Function result
        
    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return func()
        except JIRAError as e:
            last_exception = e
            
            # Don't retry on auth errors or not found
            if e.status_code in [401, 403, 404]:
                raise
            
            if attempt < max_retries - 1:
                logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay}s: {e}")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                logger.error(f"All {max_retries} retry attempts failed")
                raise last_exception
    
    raise last_exception
