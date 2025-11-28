"""S3 service for handling receipt file operations."""

from datetime import datetime
import os
from typing import Optional, Tuple
import uuid

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from flask import current_app
from werkzeug.datastructures import FileStorage


class S3Service:
    """Service for S3 file operations."""

    def __init__(self) -> None:
        """Initialize S3 service with configuration."""
        self.bucket_name: str | None = current_app.config.get("S3_RECEIPTS_BUCKET")
        self.region: str = current_app.config.get("S3_REGION", "us-east-1")
        self.prefix: str = current_app.config.get("S3_RECEIPTS_PREFIX", "receipts/")
        self.url_expiry: int = current_app.config.get("S3_URL_EXPIRY", 3600)

        # Initialize S3 client
        try:
            self.s3_client = boto3.client("s3", region_name=self.region)
            self._verify_bucket_access()
        except NoCredentialsError:
            current_app.logger.error("AWS credentials not found")
            raise
        except Exception as e:
            current_app.logger.error(f"Failed to initialize S3 client: {str(e)}")
            raise

    def _verify_bucket_access(self) -> None:
        """Verify that we can access the S3 bucket."""
        if not self.bucket_name:
            raise ValueError("S3 bucket name is not configured")
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            current_app.logger.info(f"S3 bucket access verified: {self.bucket_name}")
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                current_app.logger.error(f"S3 bucket not found: {self.bucket_name}")
                raise
            elif error_code == "403":
                current_app.logger.error(f"Access denied to S3 bucket: {self.bucket_name}")
                raise
            else:
                current_app.logger.error(f"S3 bucket access error: {str(e)}")
                raise

    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate a unique filename for S3 storage."""
        # Get file extension
        _, ext = os.path.splitext(original_filename)

        # Generate unique filename with timestamp and UUID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]

        return f"{timestamp}_{unique_id}_{original_filename}"

    def upload_receipt(self, file_storage: FileStorage) -> tuple[str | None, str | None]:
        """Upload a receipt file to S3.

        Args:
            file_storage: The uploaded file

        Returns:
            Tuple of (S3 key, error message)
        """
        try:
            # Generate unique filename
            original_filename = file_storage.filename or "unknown_file"
            filename = self._generate_unique_filename(original_filename)
            s3_key = f"{self.prefix}{filename}"

            # Upload file to S3
            if not self.bucket_name:
                return None, "S3 bucket name is not configured"
            file_storage.seek(0)  # Reset file pointer
            self.s3_client.upload_fileobj(
                file_storage,  # type: ignore[arg-type]
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    "ContentType": file_storage.content_type or "application/octet-stream",
                    "Metadata": {
                        "original_filename": file_storage.filename,
                        "uploaded_at": datetime.now().isoformat(),
                    },
                },
            )

            current_app.logger.info(f"Receipt uploaded to S3: {s3_key}")
            return s3_key, None

        except ClientError as e:
            error_msg = f"Failed to upload receipt to S3: {str(e)}"
            current_app.logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error uploading receipt: {str(e)}"
            current_app.logger.error(error_msg)
            return None, error_msg

    def delete_receipt(self, s3_key: str) -> str | None:
        """Delete a receipt file from S3.

        Args:
            s3_key: The S3 key of the file to delete

        Returns:
            Error message if failed, None if successful
        """
        try:
            if not self.bucket_name:
                return "S3 bucket name is not configured"
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            current_app.logger.info(f"Receipt deleted from S3: {s3_key}")
            return None

        except ClientError as e:
            error_msg = f"Failed to delete receipt from S3: {str(e)}"
            current_app.logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Unexpected error deleting receipt: {str(e)}"
            current_app.logger.error(error_msg)
            return error_msg

    def generate_presigned_url(self, s3_key: str) -> str | None:
        """Generate a presigned URL for accessing a receipt.

        Args:
            s3_key: The S3 key of the file

        Returns:
            Presigned URL or None if failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object", Params={"Bucket": self.bucket_name, "Key": s3_key}, ExpiresIn=self.url_expiry
            )
            current_app.logger.info(f"Generated presigned URL for: {s3_key}")
            return url

        except ClientError as e:
            current_app.logger.error(f"Failed to generate presigned URL: {str(e)}")
            return None
        except Exception as e:
            current_app.logger.error(f"Unexpected error generating presigned URL: {str(e)}")
            return None


def get_s3_service() -> S3Service | None:
    """Get S3 service instance if S3 is enabled."""
    if current_app.config.get("S3_RECEIPTS_BUCKET"):
        try:
            return S3Service()
        except Exception as e:
            current_app.logger.error(f"Failed to initialize S3 service: {str(e)}")
            return None
    return None
