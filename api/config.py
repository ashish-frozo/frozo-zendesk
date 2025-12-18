"""Application configuration using Pydantic settings."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str
    redis_url: str
    
    # S3 Storage
    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False
    
    # Zendesk
    zendesk_client_id: str
    zendesk_client_secret: str
    zendesk_redirect_uri: str
    
    # Jira
    jira_cloud_id: Optional[str] = None
    jira_api_token: Optional[str] = None
    jira_user_email: Optional[str] = None
    jira_oauth_client_id: Optional[str] = None
    jira_oauth_client_secret: Optional[str] = None
    
    # Slack
    slack_webhook_url: Optional[str] = None
    
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.3
    openai_max_tokens: int = 2000
    
    # Google Cloud Vision (OCR fallback)
    google_application_credentials: Optional[str] = None
    google_cloud_vision_key: Optional[str] = None
    
    # App
    app_secret_key: str
    cors_origins: str = "http://localhost:3000"
    
    # Defaults
    default_internal_notes_enabled: bool = False
    default_last_public_comments: int = 1
    default_pdf_max_pages: int = 10
    default_pdf_max_size_mb: int = 10
    
    # Celery
    celery_broker_url: str
    celery_result_backend: str
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
