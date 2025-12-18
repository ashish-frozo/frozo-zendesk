"""
S3-compatible storage service for sanitized artifacts.

Supports: AWS S3, Cloudflare R2, MinIO
"""

import logging
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from api.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """S3-compatible storage service."""
    
    def __init__(self):
        """Initialize S3 client."""
        self.client = boto3.client(
            's3',
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            use_ssl=settings.s3_use_ssl
        )
        self.bucket = settings.s3_bucket
    
    def upload(self, key: str, data: bytes, content_type: str = 'application/octet-stream') -> str:
        """
        Upload file to S3.
        
        Args:
            key: S3 object key
            data: File content as bytes
            content_type: MIME type
            
        Returns:
            S3 URL or key
        """
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type
            )
            
            logger.info(f"Uploaded {len(data)} bytes to s3://{self.bucket}/{key}")
            
            # Return URL
            if settings.s3_use_ssl:
                return f"https://{self.bucket}.s3.{settings.s3_region}.amazonaws.com/{key}"
            else:
                return f"{settings.s3_endpoint}/{self.bucket}/{key}"
                
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise
    
    def download(self, key: str) -> bytes:
        """Download file from S3."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"Failed to download from S3: {e}")
            raise
    
    def generate_presigned_url(self, key: str, expiration: int = 600) -> str:
        """
        Generate presigned URL for temporary access.
        
        Args:
            key: S3 object key
            expiration: URL validity in seconds (default: 10 minutes)
            
        Returns:
            Presigned URL
        """
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise


# Singleton instance
_storage_service = None

def get_storage_service() -> StorageService:
    """Get singleton storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service


def upload_to_s3(key: str, data: bytes, content_type: str = 'application/octet-stream') -> str:
    """Convenience function to upload to S3."""
    return get_storage_service().upload(key, data, content_type)


def download_from_s3(key: str) -> bytes:
    """Convenience function to download from S3."""
    return get_storage_service().download(key)


def get_presigned_url(key: str, expiration: int = 600) -> str:
    """Convenience function to get presigned URL."""
    return get_storage_service().generate_presigned_url(key, expiration)
