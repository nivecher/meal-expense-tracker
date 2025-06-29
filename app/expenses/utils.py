"""Utility functions for the expenses module."""

import os
from datetime import datetime
from pathlib import Path

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
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
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
