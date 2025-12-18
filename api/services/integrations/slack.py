"""
Slack integration service.

Handles:
- Webhook messaging
- Message formatting
- Error handling
"""

import logging
from typing import Dict, Optional
import requests

logger = logging.getLogger(__name__)


class SlackService:
    """Service for posting messages to Slack via webhook."""
    
    def __init__(self, webhook_url: str):
        """
        Initialize Slack service.
        
        Args:
            webhook_url: Slack incoming webhook URL
        """
        self.webhook_url = webhook_url
    
    def post_message(
        self,
        text: str,
        blocks: Optional[list] = None,
        channel: Optional[str] = None
    ) -> Dict:
        """
        Post message to Slack.
        
        Args:
            text: Message text (fallback)
            blocks: Slack blocks for rich formatting
            channel: Channel override (if webhook supports it)
            
        Returns:
            Response dictionary with status
        """
        try:
            payload = {"text": text}
            
            if blocks:
                payload["blocks"] = blocks
            
            if channel:
                payload["channel"] = channel
            
            logger.info(f"Posting message to Slack: {text[:100]}...")
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            response.raise_for_status()
            
            logger.info("Slack message posted successfully")
            
            return {
                "status": "success",
                "response": response.text
            }
            
        except requests.RequestException as e:
            logger.error(f"Failed to post Slack message: {e}")
            raise
    
    def post_escalation_notification(
        self,
        jira_issue_key: str,
        jira_issue_url: str,
        zendesk_ticket_id: str,
        zendesk_ticket_url: str,
        summary: str,
        severity: str = "Medium"
    ) -> Dict:
        """
        Post formatted escalation notification.
        
        Args:
            jira_issue_key: Jira issue key
            jira_issue_url: Jira issue URL
            zendesk_ticket_id: Zendesk ticket ID
            zendesk_ticket_url: Zendesk ticket URL
            summary: Sanitized summary
            severity: Severity level
            
        Returns:
            Response dictionary
        """
        # Build rich message with blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 New Escalation: {jira_issue_key}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{severity}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Zendesk Ticket:*\n<{zendesk_ticket_url}|#{zendesk_ticket_id}>"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Summary:*\n{summary}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View in Jira"
                        },
                        "url": jira_issue_url,
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Ticket"
                        },
                        "url": zendesk_ticket_url
                    }
                ]
            }
        ]
        
        fallback_text = f"New escalation: {jira_issue_key} - {summary}"
        
        return self.post_message(text=fallback_text, blocks=blocks)


def create_slack_client(webhook_url: str) -> SlackService:
    """Factory function to create Slack service instance."""
    return SlackService(webhook_url=webhook_url)
