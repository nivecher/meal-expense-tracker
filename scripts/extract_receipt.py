#!/usr/bin/env python3
"""Command-line script to extract receipt information from images or PDFs using OCR.

This script uses simple, free OCR (EasyOCR) or AWS Textract to extract structured data from receipt images or PDFs,
similar to the OCR service used in the web application.

Usage:
    python scripts/extract_receipt.py <file_path> [--output-format json|text] [--region REGION]

Requirements:
    - For EasyOCR: Install script dependencies: pip install -r requirements/scripts.txt
      Note: EasyOCR is NOT included in production requirements - it's only needed for this standalone script.
      The production web application uses AWS Textract instead.
    - For AWS Textract: AWS credentials configured (via environment variables, ~/.aws/credentials, or IAM role)
"""

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from PIL import Image

# Import unified receipt parser
# Add app directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.services.receipt_parser import ReceiptParser

# Simple, free OCR using EasyOCR (no API keys, no costs)
try:
    import easyocr

    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

# Optional dotenv for environment variables (only for Textract)
try:
    from dotenv import load_dotenv

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# Optional pdf2image for PDF processing
try:
    from pdf2image import convert_from_bytes, convert_from_path

    PDF2IMAGE_AVAILABLE = True
except ImportError:
    convert_from_path = None
    convert_from_bytes = None
    PDF2IMAGE_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class ReceiptData:
    """Structured data extracted from a receipt."""

    amount: Decimal | None = None
    date: datetime | None = None
    time: str | None = None  # Time string in HH:MM AM/PM format
    restaurant_name: str | None = None
    restaurant_location_number: str | None = None  # Location/store number (e.g., "#41", "Store 123")
    restaurant_address: str | None = None
    restaurant_phone: str | None = None
    restaurant_website: str | None = None
    server_name: str | None = None  # Server name (e.g., "Madison P.")
    customer_name: str | None = None  # Customer name (e.g., "Morgan")
    check_number: str | None = None  # Check/order number (e.g., "#32")
    table_number: str | None = None  # Table number (e.g., "12", "Table 5")
    items: list[dict[str, Any]] | None = None  # List of dicts with 'name', 'price', and 'quantity' keys
    subtotal: Decimal | None = None  # Subtotal before tax and tip
    tax: Decimal | None = None
    tip: Decimal | None = None
    total: Decimal | None = None
    confidence_scores: dict[str, float] | None = None
    raw_text: str = ""

    def __post_init__(self) -> None:
        """Initialize default values for mutable fields."""
        if self.items is None:
            self.items = []
        if self.confidence_scores is None:
            self.confidence_scores = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert ReceiptData to dictionary with serializable values."""
        result = asdict(self)
        # Convert Decimal to string for JSON serialization
        for key in ["amount", "subtotal", "tax", "tip", "total"]:
            if result[key] is not None:
                result[key] = str(result[key])
        # Convert datetime to ISO format string
        if result["date"] is not None:
            result["date"] = result["date"].isoformat()
        # Convert item prices to strings
        if result["items"]:
            for item in result["items"]:
                if isinstance(item, dict) and "price" in item and item["price"] is not None:
                    item["price"] = str(item["price"])
        return result


class SimpleOCRService:
    def __init__(self) -> None:
        """Initialize simple OCR service."""
        if not EASYOCR_AVAILABLE:
            raise RuntimeError("EasyOCR not available. Install with: pip install easyocr")

        # Initialize EasyOCR reader (English only for speed)
        self.reader = easyocr.Reader(["en"])
        self.parser = ReceiptParser()  # Unified receipt parser

    def extract_receipt_data(self, file_path: str | Path) -> ReceiptData:
        """Extract structured data from a receipt image or PDF.

        Args:
            file_path: Path to the receipt file (image or PDF)

        Returns:
            ReceiptData object with extracted fields
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise ValueError(f"File not found: {file_path}")

        # Convert PDF to image if needed
        temp_file_path = None
        if file_path_obj.suffix.lower() == ".pdf":
            try:
                import tempfile

                images = convert_from_path(str(file_path_obj))
                if not images:
                    raise RuntimeError("PDF conversion produced no images")

                # For multi-page receipts, combine pages 1 and 2
                # Page 1 typically has header info, page 2 has items
                if len(images) >= 2:
                    from PIL import Image

                    # Get dimensions for combined image
                    width = max(img.width for img in images[:2])
                    height = sum(img.height for img in images[:2])

                    # Create combined image
                    combined_img = Image.new("RGB", (width, height), "white")
                    y_offset = 0

                    for img in images[:2]:  # Process first 2 pages
                        combined_img.paste(img, (0, y_offset))
                        y_offset += img.height

                    # Save combined image
                    temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                    combined_img.save(temp_file.name, "JPEG")
                    image_path = temp_file.name
                    temp_file_path = temp_file.name
                else:
                    # Single page - use it as-is
                    temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                    images[0].save(temp_file.name, "JPEG")
                    image_path = temp_file.name
                    temp_file_path = temp_file.name
            except ImportError:
                raise RuntimeError("PDF processing requires pdf2image: pip install pdf2image")
            if not PDF2IMAGE_AVAILABLE:
                raise RuntimeError("PDF processing requires pdf2image: pip install pdf2image")
        else:
            image_path = str(file_path_obj)

        try:
            # Extract text with EasyOCR
            results = self.reader.readtext(image_path)
            raw_text = "\n".join([text for (_, text, _) in results])
        except Exception as e:
            raise RuntimeError(f"OCR failed: {e}")
        finally:
            # Clean up temporary file if it was created
            if temp_file_path and os.path.exists(temp_file_path):
                Path(temp_file_path).unlink()

        # Parse receipt data from raw text using unified parser
        receipt_data = ReceiptData(raw_text=raw_text)
        receipt_data = self.parser.parse_receipt_data(raw_text, receipt_data)

        # Calculate basic confidence scores
        receipt_data.confidence_scores = {
            "merchant_name": 0.8 if receipt_data.restaurant_name else 0.0,
            "total": 0.9 if receipt_data.total else 0.0,
            "date": 0.7 if receipt_data.date else 0.0,
            "items": min(0.6, len(receipt_data.items) * 0.1) if receipt_data.items else 0.0,
        }

        return receipt_data


class StandaloneOCRService:
    def __init__(self, region: str = "us-east-1", confidence_threshold: float = 0.7) -> None:
        """Initialize OCR service with configuration.

        Args:
            region: AWS region for Textract (default: us-east-1)
            confidence_threshold: Minimum confidence threshold (not used in current implementation)
        """
        self.confidence_threshold = confidence_threshold
        self.region = region
        self.parser = ReceiptParser()  # Unified receipt parser

        # Verify Textract is available
        try:
            self.textract_client = boto3.client("textract", region_name=self.region)
            logger.info(f"AWS Textract initialized successfully (region: {self.region})")
        except NoCredentialsError:
            logger.error(
                "AWS credentials not found. Please configure AWS credentials:\n"
                "  - Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables\n"
                "  - Or configure ~/.aws/credentials\n"
                "  - Or use IAM role (for Lambda/ECS deployments)"
            )
            raise RuntimeError("AWS credentials not found") from None
        except Exception as e:
            logger.error(f"AWS Textract not available: {e}")
            raise RuntimeError(f"AWS Textract initialization failed: {e}") from e

    def extract_receipt_data(self, file_path: str | Path) -> ReceiptData:
        """Extract structured data from a receipt image or PDF.

        Args:
            file_path: Path to the receipt file (image or PDF)

        Returns:
            ReceiptData object with extracted fields

        Raises:
            ValueError: If file format is not supported or file doesn't exist
            RuntimeError: If OCR processing fails
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise ValueError(f"File not found: {file_path}")

        # Read file content
        with open(file_path_obj, "rb") as f:
            file_bytes = f.read()

        # Extract text using AWS Textract (handles both images and PDFs natively)
        try:
            raw_text = self._extract_text_with_textract(file_bytes, str(file_path_obj))
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"AWS Textract error ({error_code}): {error_message}")
            raise RuntimeError(f"Failed to extract text with AWS Textract: {error_message}") from e
        except Exception as e:
            logger.error(f"OCR text extraction failed: {e}")
            raise RuntimeError(f"Failed to extract text: {e}") from e

        # Log raw OCR text for debugging - show ALL text
        logger.debug("=" * 60)
        logger.debug("RAW OCR TEXT (full text):")
        logger.debug("=" * 60)
        if raw_text:
            # Log in chunks of 1000 chars to avoid overwhelming logs
            chunk_size = 1000
            for i in range(0, len(raw_text), chunk_size):
                chunk = raw_text[i : i + chunk_size]
                logger.debug(f"Chunk {i // chunk_size + 1} (chars {i}-{min(i + chunk_size, len(raw_text))}):")
                logger.debug(chunk)
            logger.debug(f"\nTotal characters extracted: {len(raw_text)}")
        else:
            logger.debug("No text extracted from OCR")
        logger.debug("=" * 60)

        # Parse receipt data from extracted text using unified parser
        receipt_data = ReceiptData(raw_text=raw_text)
        receipt_data = self.parser.parse_receipt_data(raw_text, receipt_data)

        return receipt_data

    def _extract_text_with_textract(self, file_bytes: bytes, filename: str) -> str:
        """Extract text using AWS Textract with automatic PDF fallback.

        Args:
            file_bytes: Raw file bytes (image or PDF)
            filename: Original filename for format detection

        Returns:
            Extracted text string

        Raises:
            ValueError: If file format is unsupported or processing fails
            RuntimeError: If text extraction fails
        """
        if not self.textract_client:
            raise RuntimeError("Textract client not initialized")

        # Validate file size (Textract has a 5MB limit for synchronous operations)
        max_size = 5 * 1024 * 1024  # 5MB
        if len(file_bytes) > max_size:
            raise ValueError(
                f"File size ({len(file_bytes)} bytes) exceeds Textract limit ({max_size} bytes). "
                "Use asynchronous AnalyzeDocument for larger files."
            )

        # Detect file format
        is_pdf = filename.lower().endswith(".pdf") or file_bytes[:4] == b"%PDF"
        is_jpeg = filename.lower().endswith((".jpg", ".jpeg")) or file_bytes[:2] == b"\xff\xd8"
        is_png = filename.lower().endswith(".png") or file_bytes[:8] == b"\x89PNG\r\n\x1a\n"

        if not (is_pdf or is_jpeg or is_png):
            raise ValueError(
                f"Unsupported file format. AWS Textract only supports PNG, JPEG, and PDF formats. " f"File: {filename}"
            )

        # Try direct Textract processing first
        try:
            return self._extract_text_from_image_or_pdf(file_bytes, filename, is_pdf)
        except (ClientError, ValueError, Exception) as e:
            # For PDFs, try fallback conversion to image for any error
            # (PDFs can fail for various reasons: unsupported encodings, complex structure, etc.)
            if is_pdf:
                # Skip fallback only for specific non-format errors
                if self._should_skip_fallback(e):
                    raise

                # Try fallback: convert PDF to image
                if PDF2IMAGE_AVAILABLE:
                    logger.info(
                        f"Textract failed on PDF directly, attempting fallback: convert PDF to image for {filename}"
                    )
                    try:
                        return self._extract_text_from_pdf_via_image_fallback(file_bytes, filename)
                    except Exception as fallback_error:
                        logger.error(f"PDF to image fallback also failed for {filename}: {fallback_error}")
                        # If original error was format-related, preserve that context
                        if self._is_unsupported_format_error(e):
                            raise ValueError(
                                f"Unsupported document format. The PDF may contain unsupported image encodings "
                                f"(e.g., JPEG 2000) or have a complex structure. "
                                f"Attempted fallback conversion to image also failed. "
                                f"File: {filename}. "
                                f"Try converting the PDF to images (PNG/JPEG) manually or use a different PDF."
                            ) from fallback_error
                        # Otherwise, provide generic error
                        raise RuntimeError(
                            f"Failed to process PDF. Direct Textract processing failed, and fallback conversion "
                            f"to image also failed. File: {filename}. "
                            f"Error: {fallback_error}"
                        ) from fallback_error
                else:
                    # Fallback not available - provide helpful error message
                    if self._is_unsupported_format_error(e):
                        raise ValueError(
                            f"Unsupported document format. The PDF may contain unsupported image encodings "
                            f"(e.g., JPEG 2000) or have a complex structure. "
                            f"PDF to image conversion not available. Install pdf2image: pip install pdf2image. "
                            f"File: {filename}. "
                            f"Try converting the PDF to images (PNG/JPEG) manually or use a different PDF."
                        ) from e
                    raise RuntimeError(
                        f"Failed to process PDF. PDF to image conversion not available. "
                        f"Install pdf2image: pip install pdf2image. File: {filename}. Error: {e}"
                    ) from e

            # For non-PDF files, re-raise the error
            raise

    def _extract_text_from_image_or_pdf(self, file_bytes: bytes, filename: str, is_pdf: bool) -> str:
        """Extract text from image or PDF using AWS Textract (no fallback).

        This method directly calls Textract without attempting fallback conversion.
        Used internally to prevent recursion in fallback scenarios.

        Args:
            file_bytes: Raw file bytes (image or PDF)
            filename: Original filename for logging
            is_pdf: Whether the file is a PDF

        Returns:
            Extracted text string

        Raises:
            ClientError: If AWS Textract API call fails
            ValueError: If processing fails
        """
        logger.debug(
            f"Calling AWS Textract detect_document_text for file: {filename} "
            f"({len(file_bytes)} bytes, PDF: {is_pdf})"
        )

        try:
            response = self.textract_client.detect_document_text(Document={"Bytes": file_bytes})
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"AWS Textract API error ({error_code}): {error_message} for file: {filename}")

            if error_code == "InvalidParameterException":
                raise ValueError(f"Invalid document parameters. File: {filename}. " f"Error: {error_message}") from e

            # Re-raise to let caller handle fallback logic
            raise

        # Log response metadata for debugging
        if response.get("DocumentMetadata"):
            pages = response["DocumentMetadata"].get("Pages", 0)
            logger.debug(f"Textract processed {pages} page(s)")

        # Extract text blocks - Textract returns blocks with different types
        # We want LINE blocks for complete text extraction
        text_lines = []
        for block in response.get("Blocks", []):
            if block.get("BlockType") == "LINE":
                text = block.get("Text", "")
                if text:
                    text_lines.append(text)

        raw_text = "\n".join(text_lines)

        # Log extraction details
        logger.debug(f"Extracted {len(raw_text)} characters from {len(text_lines)} lines using AWS Textract")

        # Warn if no text was extracted
        if not raw_text or len(raw_text.strip()) < 10:
            logger.warning(
                f"Textract returned minimal or no text for {filename}. "
                f"This may indicate an unsupported PDF structure or encoding."
            )

        # Log confidence scores if available
        if response.get("Blocks"):
            line_blocks = [b for b in response["Blocks"] if b.get("BlockType") == "LINE"]
            if line_blocks:
                avg_confidence = sum(block.get("Confidence", 0) for block in line_blocks) / len(line_blocks)
                logger.debug(f"Average confidence: {avg_confidence:.2f}%")

        return raw_text

    def _should_skip_fallback(self, error: Exception) -> bool:
        """Check if fallback should be skipped for this error.

        Some errors (like invalid parameters) won't be fixed by PDF-to-image conversion,
        so we should skip the fallback and raise the error directly.

        Args:
            error: Exception to check

        Returns:
            True if fallback should be skipped
        """
        if isinstance(error, ClientError):
            error_code = error.response.get("Error", {}).get("Code", "Unknown")

            # Skip fallback for parameter errors (won't be fixed by conversion)
            if error_code == "InvalidParameterException":
                return True

            # Skip fallback for authentication/authorization errors
            if error_code in ("AccessDeniedException", "UnauthorizedOperation"):
                return True

        if isinstance(error, ValueError):
            error_str = str(error).lower()

            # Skip fallback for file size errors (conversion won't help)
            if "file size" in error_str and "exceeds" in error_str:
                return True

            # Skip fallback for unsupported file format (not a PDF)
            if "unsupported file format" in error_str and "pdf" not in error_str:
                return True

        return False

    def _is_unsupported_format_error(self, error: Exception) -> bool:
        """Check if error indicates unsupported document format.

        Args:
            error: Exception to check

        Returns:
            True if error indicates unsupported format
        """
        if isinstance(error, ClientError):
            error_code = error.response.get("Error", {}).get("Code", "Unknown")
            error_message = error.response.get("Error", {}).get("Message", "").lower()

            # Check error code
            if error_code == "UnsupportedDocumentException":
                return True

            # Check error message for format-related keywords
            format_keywords = [
                "unsupported document format",
                "unsupported image encoding",
                "jpeg 2000",
                "complex structure",
            ]
            if any(keyword in error_message for keyword in format_keywords):
                return True

        if isinstance(error, ValueError):
            error_str = str(error).lower()
            format_keywords = [
                "unsupported document format",
                "unsupported image encoding",
                "jpeg 2000",
                "complex structure",
            ]
            if any(keyword in error_str for keyword in format_keywords):
                return True

        return False

    def _extract_text_from_pdf_via_image_fallback(self, pdf_bytes: bytes, filename: str) -> str:
        """Fallback method: Convert PDF to image, then process with Textract.

        This is used when Textract cannot process a PDF directly (e.g., due to
        unsupported image encodings like JPEG 2000).

        Args:
            pdf_bytes: Raw PDF file bytes
            filename: Original filename for logging

        Returns:
            Extracted text string

        Raises:
            RuntimeError: If conversion or processing fails
        """
        if not PDF2IMAGE_AVAILABLE:
            raise RuntimeError("PDF to image conversion not available. Install pdf2image: pip install pdf2image")

        # Check if poppler is available (pdf2image requires it)
        self._verify_poppler_available()

        logger.debug(f"Converting PDF to image for fallback processing: {filename}")

        try:
            # Convert first page of PDF to image at 300 DPI (good balance of quality/size)
            images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1, dpi=300)

            if not images:
                raise RuntimeError("PDF conversion produced no images")

            # Convert PIL Image to bytes for Textract
            img = images[0]

            # Convert to RGB if necessary
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Save to bytes buffer
            img_buffer = BytesIO()
            img.save(img_buffer, format="PNG")
            img_bytes = img_buffer.getvalue()

            logger.debug(f"Converted PDF to PNG image: {img.size}, {len(img_bytes)} bytes")

            # Process the image with Textract (use direct method to prevent recursion)
            return self._extract_text_from_image_or_pdf(img_bytes, filename.replace(".pdf", ".png"), False)

        except Exception as e:
            logger.error(f"PDF to image conversion failed: {e}")
            raise RuntimeError(f"Failed to convert PDF to image: {e}") from e

    def _verify_poppler_available(self) -> None:
        """Verify that poppler-utils is installed and available.

        Raises:
            RuntimeError: If poppler is not available
        """
        try:
            result = subprocess.run(
                ["pdftoppm", "-v"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    "Poppler (pdftoppm) is not installed or not in PATH. "
                    "Install poppler-utils:\n"
                    "  Linux/WSL: sudo apt-get install poppler-utils\n"
                    "  macOS: brew install poppler\n"
                    "  Or run: scripts/setup-local-dev.sh --mode full"
                )
        except FileNotFoundError:
            raise RuntimeError(
                "Poppler (pdftoppm) is not installed or not in PATH. "
                "Install poppler-utils:\n"
                "  Linux/WSL: sudo apt-get install poppler-utils\n"
                "  macOS: brew install poppler\n"
                "  Or run: scripts/setup-local-dev.sh --mode full"
            ) from None
        except Exception as e:
            logger.warning(f"Could not verify poppler installation: {e}")


def format_output_text(receipt_data: ReceiptData) -> str:
    """Format receipt data as human-readable text with sections and tables.

    Args:
        receipt_data: ReceiptData object

    Returns:
        Formatted text string
    """
    lines = []
    lines.append("=" * 80)
    lines.append("RAW TEXT (first 500 chars)")
    lines.append("=" * 80)
    lines.append(receipt_data.raw_text[:500])
    if len(receipt_data.raw_text) > 500:
        lines.append("...")
        lines.append(f"(truncated, total length: {len(receipt_data.raw_text)} characters)")

    lines.append("")
    lines.append("=" * 80)
    lines.append("RECEIPT EXTRACTION RESULTS")
    lines.append("=" * 80)
    lines.append("")

    # RESTAURANT INFORMATION SECTION
    lines.append("┌─ RESTAURANT INFORMATION ─────────────────────────────────────────────┐")
    restaurant_info = []
    if receipt_data.restaurant_name:
        restaurant_display = receipt_data.restaurant_name
        if receipt_data.restaurant_location_number:
            restaurant_display += f" ({receipt_data.restaurant_location_number})"
        restaurant_info.append(("Restaurant", restaurant_display))
    else:
        restaurant_info.append(("Restaurant", "(not found)"))

    if receipt_data.restaurant_address:
        restaurant_info.append(("Address", receipt_data.restaurant_address))
    if receipt_data.restaurant_phone:
        restaurant_info.append(("Phone", receipt_data.restaurant_phone))
    if receipt_data.restaurant_website:
        restaurant_info.append(("Website", receipt_data.restaurant_website))
    if receipt_data.restaurant_location_number:
        restaurant_info.append(("Location #", receipt_data.restaurant_location_number))

    # Format as table
    if restaurant_info:
        max_key_len = max(len(k) for k, _ in restaurant_info)
        for key, value in restaurant_info:
            lines.append(f"│ {key:<{max_key_len}} │ {value}")
    lines.append("└" + "─" * 78 + "┘")
    lines.append("")

    # ORDER INFORMATION SECTION
    lines.append("┌─ ORDER INFORMATION ─────────────────────────────────────────────────┐")
    order_info = []
    if receipt_data.date:
        # Combine date and time if time is available
        if receipt_data.time:
            time_str = receipt_data.time.strip()
            try:
                # Try parsing 12-hour format with AM/PM
                if "AM" in time_str.upper() or "PM" in time_str.upper():
                    time_part = re.search(r"(\d{1,2}):(\d{2})\s*(AM|PM)", time_str, re.IGNORECASE)
                    if time_part:
                        hour = int(time_part.group(1))
                        minute = int(time_part.group(2))
                        am_pm = time_part.group(3).upper()
                        if am_pm == "PM" and hour != 12:
                            hour += 12
                        elif am_pm == "AM" and hour == 12:
                            hour = 0
                        combined_datetime = receipt_data.date.replace(hour=hour, minute=minute, second=0)
                        order_info.append(("Date/Time", combined_datetime.strftime("%Y-%m-%d %H:%M:%S")))
                    else:
                        order_info.append(("Date/Time", f"{receipt_data.date.strftime('%Y-%m-%d')} {time_str}"))
                else:
                    time_part = re.search(r"(\d{1,2}):(\d{2})", time_str)
                    if time_part:
                        hour = int(time_part.group(1))
                        minute = int(time_part.group(2))
                        combined_datetime = receipt_data.date.replace(hour=hour, minute=minute, second=0)
                        order_info.append(("Date/Time", combined_datetime.strftime("%Y-%m-%d %H:%M:%S")))
                    else:
                        order_info.append(("Date/Time", f"{receipt_data.date.strftime('%Y-%m-%d')} {time_str}"))
            except (ValueError, AttributeError):
                order_info.append(("Date/Time", f"{receipt_data.date.strftime('%Y-%m-%d')} {time_str}"))
        else:
            order_info.append(("Date", receipt_data.date.strftime("%Y-%m-%d")))
    else:
        order_info.append(("Date", "(not found)"))

    if receipt_data.check_number:
        order_info.append(("Check #", receipt_data.check_number))
    if receipt_data.table_number:
        order_info.append(("Table", receipt_data.table_number))
    if receipt_data.server_name:
        order_info.append(("Server", receipt_data.server_name))
    if receipt_data.customer_name:
        order_info.append(("Customer", receipt_data.customer_name))

    # Format as table
    if order_info:
        max_key_len = max(len(k) for k, _ in order_info)
        for key, value in order_info:
            lines.append(f"│ {key:<{max_key_len}} │ {value}")
    lines.append("└" + "─" * 78 + "┘")
    lines.append("")

    # ITEMS SECTION
    if receipt_data.items:
        lines.append("┌─ ITEMS ───────────────────────────────────────────────────────────┐")
        lines.append(f"│ {'Qty':>3} │ {'Item':<45} │ {'Price':>10} │")
        lines.append("├" + "─" * 5 + "┼" + "─" * 47 + "┼" + "─" * 12 + "┤")
        for item in receipt_data.items:
            if isinstance(item, dict):
                item_name = item.get("name", "")
                item_price = item.get("price")
                item_quantity = item.get("quantity", 1.0)
                if item_price is not None:
                    price_str = f"${item_price:.2f}"
                else:
                    price_str = "$0.00"
                quantity_str = f"{item_quantity:.0f}" if item_quantity == int(item_quantity) else f"{item_quantity:.1f}"
            else:
                # Backward compatibility: if item is a string
                item_name = str(item)
                price_str = "N/A"
                quantity_str = "1"
            # Truncate long item names
            if len(item_name) > 45:
                item_name = item_name[:42] + "..."
            lines.append(f"│ {quantity_str:>3} │ {item_name:<45} │ {price_str:>10} │")
        lines.append("└" + "─" * 5 + "┴" + "─" * 47 + "┴" + "─" * 12 + "┘")
        lines.append("")

    # TOTALS SECTION
    lines.append("┌─ TOTALS ────────────────────────────────────────────────────────────┐")
    totals_info = []

    # Show subtotal
    if receipt_data.subtotal:
        totals_info.append(("Subtotal", f"${receipt_data.subtotal:.2f}"))

    # Show tax
    if receipt_data.tax:
        totals_info.append(("Tax", f"${receipt_data.tax:.2f}"))

    # Calculate and show total (subtotal + tax, before tip)
    pre_tip_total = None
    if receipt_data.subtotal and receipt_data.tax:
        pre_tip_total = receipt_data.subtotal + receipt_data.tax
        totals_info.append(("Total", f"${pre_tip_total:.2f}"))
    elif receipt_data.total and not receipt_data.tip:
        # If no tip, total is the pre-tip total
        pre_tip_total = receipt_data.total
        totals_info.append(("Total", f"${pre_tip_total:.2f}"))

    # Show Gratuity / Tip
    if receipt_data.tip:
        totals_info.append(("Gratuity / Tip", f"${receipt_data.tip:.2f}"))

    # Amount (Paid) - this is what was actually charged/paid (total + tip)
    if receipt_data.amount:
        totals_info.append(("Amount (Paid)", f"${receipt_data.amount:.2f}"))
    elif pre_tip_total and receipt_data.tip:
        # Calculate amount paid as pre-tip total + tip
        amount_paid = pre_tip_total + receipt_data.tip
        totals_info.append(("Amount (Paid)", f"${amount_paid:.2f}"))

    # Format as table
    if totals_info:
        max_key_len = max(len(k) for k, _ in totals_info)
        for key, value in totals_info:
            lines.append(f"│ {key:<{max_key_len}} │ {value:>10}")
    lines.append("└" + "─" * 78 + "┘")
    lines.append("")

    # CONFIDENCE SCORES (if available)
    if receipt_data.confidence_scores:
        lines.append("┌─ CONFIDENCE SCORES ─────────────────────────────────────────────┐")
        max_key_len = max(len(k) for k in receipt_data.confidence_scores.keys())
        for field, score in receipt_data.confidence_scores.items():
            lines.append(f"│ {field:<{max_key_len}} │ {score:>6.1%}")
        lines.append("└" + "─" * 78 + "┘")

    return "\n".join(lines)


def main() -> int:
    """Main entry point for the command-line script.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = argparse.ArgumentParser(
        description="Extract receipt information from images or PDFs using OCR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using EasyOCR (free, recommended)
  python scripts/extract_receipt.py receipt.jpg
  python scripts/extract_receipt.py receipt.pdf --output-format json

  # Using AWS Textract
  python scripts/extract_receipt.py receipt.jpg --ocr-engine textract --region us-west-2

Note: EasyOCR is free and requires no API keys or internet connection.
      AWS Textract requires AWS credentials configured via environment variables,
      ~/.aws/credentials, or IAM role.
        """,
    )
    parser.add_argument(
        "file_path",
        type=str,
        help="Path to receipt image or PDF file",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="text",
        help="Output format: 'json' for JSON, 'text' for human-readable (default: text)",
    )
    parser.add_argument(
        "--ocr-engine",
        choices=["easyocr", "textract"],
        default="easyocr",
        help="OCR engine to use: 'easyocr' (free, local) or 'textract' (AWS, default: easyocr)",
    )
    parser.add_argument(
        "--region",
        type=str,
        default="us-east-1",
        help="AWS region for Textract (default: us-east-1, ignored for easyocr)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load environment variables
    if DOTENV_AVAILABLE:
        load_dotenv()

    # Validate file exists
    file_path = Path(args.file_path)
    if not file_path.exists():
        logger.error(f"File not found: {args.file_path}")
        return 1

    try:
        # Initialize appropriate OCR service
        if args.ocr_engine == "easyocr":
            if not EASYOCR_AVAILABLE:
                logger.error("EasyOCR not available. Install with: pip install easyocr")
                return 1

            logger.info("Using EasyOCR (free, local)")
            ocr_service = SimpleOCRService()
        else:
            logger.info(f"Using AWS Textract (region: {args.region})")
            ocr_service = StandaloneOCRService(
                region=args.region,
                confidence_threshold=0.7,
            )

        # Extract receipt data
        logger.info(f"Processing file: {args.file_path}")
        receipt_data = ocr_service.extract_receipt_data(file_path)

        # Output results
        if args.output_format == "json":
            output_dict = receipt_data.to_dict()
            print(json.dumps(output_dict, indent=2))
        else:
            print(format_output_text(receipt_data))

        return 0

    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return 1
    except RuntimeError as e:
        logger.error(f"OCR processing failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
