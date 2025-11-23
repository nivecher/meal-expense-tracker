"""Utility functions for the expenses module."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from werkzeug.datastructures import FileStorage


def save_receipt(file_storage: FileStorage, upload_folder: str) -> str:
    """Save an uploaded receipt file to the filesystem.

    Args:
        file_storage: The uploaded file from request.files
        upload_folder: The base directory where files should be saved

    Returns:
        str: The path where the file was saved, relative to the upload folder

    Raises:
        OSError: If there's an error creating directories or saving the file
        ValueError: If the file extension is not allowed
    """
    # Ensure the upload directory exists
    os.makedirs(upload_folder, exist_ok=True)

    # Generate a unique filename
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    original_filename = file_storage.filename or "receipt"
    file_ext = Path(original_filename).suffix.lower()

    # Validate file extension
    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png", ".gif"}
    if file_ext not in allowed_extensions:
        raise ValueError(f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}")

    # Create a safe filename
    safe_filename = f"{timestamp}_{Path(original_filename).stem}{file_ext}"
    filepath = os.path.join(upload_folder, safe_filename)

    # Save the file
    file_storage.save(filepath)

    # Return the relative path
    return safe_filename


def save_receipt_to_storage(file_storage: FileStorage, upload_folder: str) -> Tuple[Optional[str], Optional[str]]:
    """Save a receipt file to either local storage or S3 based on configuration.

    Args:
        file_storage: The uploaded file from request.files
        upload_folder: The base directory for local storage (ignored for S3)

    Returns:
        Tuple of (storage_path, error_message)
        - storage_path: S3 key if using S3, local filename if using local storage
        - error_message: Error message if failed, None if successful
    """
    from flask import current_app

    # Check if S3 is enabled (bucket name configured)
    if current_app.config.get("S3_RECEIPTS_BUCKET"):
        try:
            from app.services.s3_service import get_s3_service

            s3_service = get_s3_service()
            if not s3_service:
                return None, "S3 service not available"

            s3_key, error = s3_service.upload_receipt(file_storage)
            return s3_key, error

        except Exception as e:
            current_app.logger.error(f"Failed to upload to S3: {str(e)}")
            return None, f"Failed to upload to S3: {str(e)}"
    else:
        # Use local storage
        try:
            filename = save_receipt(file_storage, upload_folder)
            return filename, None
        except Exception as e:
            current_app.logger.error(f"Failed to save locally: {str(e)}")
            return None, f"Failed to save locally: {str(e)}"


def delete_receipt_from_storage(storage_path: str, upload_folder: str) -> Optional[str]:
    """Delete a receipt file from either local storage or S3 based on configuration.

    Args:
        storage_path: The storage path (S3 key or local filename)
        upload_folder: The base directory for local storage (ignored for S3)

    Returns:
        Error message if failed, None if successful
    """
    from flask import current_app

    # Check if S3 is enabled (bucket name configured)
    if current_app.config.get("S3_RECEIPTS_BUCKET"):
        try:
            from app.services.s3_service import get_s3_service

            s3_service = get_s3_service()
            if not s3_service:
                return "S3 service not available"

            return s3_service.delete_receipt(storage_path)

        except Exception as e:
            current_app.logger.error(f"Failed to delete from S3: {str(e)}")  # nosec B608
            return f"Failed to delete from S3: {str(e)}"  # nosec B608
    else:
        # Use local storage
        try:
            file_path = os.path.join(upload_folder, storage_path)
            if os.path.exists(file_path):
                os.remove(file_path)
                current_app.logger.info(f"Local file deleted: {file_path}")
            return None
        except Exception as e:
            current_app.logger.error(f"Failed to delete local file: {str(e)}")
            return f"Failed to delete local file: {str(e)}"


def get_receipt_url(storage_path: str) -> Optional[str]:
    """Get a URL for accessing a receipt file.

    Args:
        storage_path: The storage path (S3 key or local filename)

    Returns:
        URL for accessing the file, or None if failed
    """
    from flask import current_app, url_for

    # Check if S3 is enabled (bucket name configured)
    if current_app.config.get("S3_RECEIPTS_BUCKET"):
        try:
            from app.services.s3_service import get_s3_service

            s3_service = get_s3_service()
            if not s3_service:
                return None

            return s3_service.generate_presigned_url(storage_path)

        except Exception as e:
            current_app.logger.error(f"Failed to generate S3 URL: {str(e)}")
            return None
    else:
        # Use local storage URL
        try:
            filename = storage_path.split("/")[-1]  # Get just the filename
            return url_for("main.serve_uploaded_file", filename=filename)
        except Exception as e:
            current_app.logger.error(f"Failed to generate local URL: {str(e)}")
            return None
