"""OCR service for extracting data from receipt images using AWS Textract."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
import shutil
from typing import Any, Callable, cast

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from flask import current_app
from pdf2image import convert_from_bytes
from PIL import Image
from werkzeug.datastructures import FileStorage

from app.services.receipt_parser import ReceiptParser


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
    items: list[str] | None = None
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


class OCRService:
    """Service for extracting text and data from receipt images using AWS Textract."""

    def __init__(self) -> None:
        """Initialize OCR service with configuration."""
        self.enabled = current_app.config.get("OCR_ENABLED", True)
        self.confidence_threshold = current_app.config.get("OCR_CONFIDENCE_THRESHOLD", 0.7)
        self.region = current_app.config.get("TEXTRACT_REGION", "us-east-1")
        self.role_arn = current_app.config.get("TEXTRACT_ROLE_ARN")
        self.parser = ReceiptParser()  # Unified receipt parser

        # Verify Textract is available
        if self.enabled:
            try:
                self.textract_client = boto3.client("textract", region_name=self.region)
                # Test connection with a simple call (will fail if credentials are missing)
                current_app.logger.info("AWS Textract initialized successfully")
            except NoCredentialsError:
                current_app.logger.error(
                    "AWS credentials not found. Please configure AWS credentials:\n"
                    "  - Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables\n"
                    "  - Or configure ~/.aws/credentials\n"
                    "  - Or use IAM role (for Lambda/ECS deployments)"
                )
                self.enabled = False
            except Exception as e:
                current_app.logger.warning(f"AWS Textract not available: {e}")
                self.enabled = False
                self.textract_client = None
        else:
            self.textract_client = None

    def extract_receipt_data(
        self,
        file_storage: FileStorage,
        form_hints: dict[str, Any] | None = None,
    ) -> ReceiptData:
        """Extract structured data from a receipt image or PDF.

        Args:
            file_storage: The uploaded receipt file
            form_hints: Optional dictionary with form values to use as hints for matching:
                - amount: Expected amount (Decimal or str)
                - date: Expected date (datetime or str)
                - restaurant_name: Expected restaurant name (str)

        Returns:
            ReceiptData object with extracted fields

        Raises:
            ValueError: If OCR is disabled or file format is not supported
            RuntimeError: If OCR processing fails or Tesseract is not installed
        """
        if not self.enabled:
            raise RuntimeError(
                "OCR is disabled. AWS Textract is not available. "
                "Please configure AWS credentials:\n"
                "  - Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables\n"
                "  - Or configure ~/.aws/credentials\n"
                "  - Or use IAM role (for Lambda/ECS deployments)"
            )

        if not file_storage or not file_storage.filename:
            raise ValueError("No file provided")

        # Read file content
        file_storage.seek(0)
        file_bytes = file_storage.read()
        file_storage.seek(0)  # Reset for potential reuse

        current_app.logger.debug(f"File size: {len(file_bytes)} bytes")
        current_app.logger.debug(f"File type detection: {file_storage.filename}")

        # Check if file is a PDF
        is_pdf = file_storage.filename.lower().endswith(".pdf") or file_bytes[:4] == b"%PDF"
        current_app.logger.debug(f"Is PDF: {is_pdf}")

        # Extract text using AWS Textract (handles both images and PDFs natively)
        # Note: _extract_text_with_textract handles PDF fallback automatically
        try:
            raw_text = self._extract_text_with_textract(file_bytes, file_storage.filename)
        except ValueError as e:
            # ValueError indicates unsupported format or invalid parameters
            # Re-raise as-is (already user-friendly)
            current_app.logger.error(f"OCR text extraction failed: {e}")
            raise
        except Exception as e:
            # Other errors (RuntimeError, ClientError, etc.)
            current_app.logger.error(f"OCR text extraction failed: {e}")
            raise RuntimeError(f"Failed to extract text: {e}") from e

        # Log raw OCR text for debugging - show ALL text
        current_app.logger.debug("=" * 60)
        current_app.logger.debug("RAW OCR TEXT (full text):")
        current_app.logger.debug("=" * 60)
        if raw_text:
            # Log in chunks of 1000 chars to avoid overwhelming logs
            chunk_size = 1000
            for i in range(0, len(raw_text), chunk_size):
                chunk = raw_text[i : i + chunk_size]
                current_app.logger.debug(f"Chunk {i//chunk_size + 1} (chars {i}-{min(i+chunk_size, len(raw_text))}):")
                current_app.logger.debug(chunk)
            current_app.logger.debug(f"\nTotal characters extracted: {len(raw_text)}")
        else:
            current_app.logger.debug("No text extracted from OCR")
        current_app.logger.debug("=" * 60)

        # Log form hints if provided
        if form_hints:
            current_app.logger.debug("\nForm hints provided:")
            for key, value in form_hints.items():
                current_app.logger.debug(f"  {key}: {value}")
        else:
            current_app.logger.debug("No form hints provided")

        # Parse receipt data from extracted text, using form hints if provided
        receipt_data = self._parse_receipt_data(raw_text, form_hints=form_hints)

        # Log final parsed results
        current_app.logger.debug("=" * 60)
        current_app.logger.debug("FINAL PARSED RECEIPT DATA:")
        current_app.logger.debug("=" * 60)
        current_app.logger.debug(f"Restaurant: {receipt_data.restaurant_name}")
        current_app.logger.debug(f"Date: {receipt_data.date}")
        current_app.logger.debug(f"Amount: {receipt_data.amount}")
        current_app.logger.debug(f"Total: {receipt_data.total}")
        current_app.logger.debug(f"Tax: {receipt_data.tax}")
        current_app.logger.debug(f"Tip: {receipt_data.tip}")
        current_app.logger.debug(f"Time: {receipt_data.time}")
        current_app.logger.debug(f"Restaurant Address: {receipt_data.restaurant_address}")
        current_app.logger.debug(f"Restaurant Location Number: {receipt_data.restaurant_location_number}")
        current_app.logger.debug(f"Restaurant Phone Number: {receipt_data.restaurant_phone}")
        current_app.logger.debug(f"Restaurant Website: {receipt_data.restaurant_website}")
        current_app.logger.debug(f"Items: {len(receipt_data.items) if receipt_data.items else 0} items")
        current_app.logger.debug("=" * 60)

        return receipt_data

    def _parse_receipt_data(
        self,
        raw_text: str,
        form_hints: dict[str, Any] | None = None,
    ) -> ReceiptData:
        """Parse receipt data from extracted text using unified ReceiptParser.

        Args:
            raw_text: Raw text extracted from OCR
            form_hints: Optional dictionary with form values to use as hints for matching

        Returns:
            ReceiptData object with parsed fields
        """
        receipt_data = ReceiptData(raw_text=raw_text)

        # Use unified parser to extract data (modifies receipt_data in place)
        self.parser.parse_receipt_data(raw_text, receipt_data)

        # Apply form hints if provided (for amount matching)
        if form_hints and form_hints.get("amount"):
            try:
                expected_amount = Decimal(str(form_hints["amount"]))
                # If we found amounts, pick the one closest to expected
                found_amounts = [v for v in [receipt_data.total, receipt_data.amount] if v is not None]
                if found_amounts:
                    closest = min(found_amounts, key=lambda x: abs(x - expected_amount))
                    # If close match (within $5), use it
                    if abs(closest - expected_amount) <= Decimal("5.00"):
                        receipt_data.total = closest
                        receipt_data.amount = closest
            except (InvalidOperation, ValueError):
                pass  # Use extracted amounts as-is

        # Convert dict items to strings for backward compatibility (web app expects list[str])
        # Parser returns list[dict] but web app expects list[str]
        if receipt_data.items:
            # Type checker doesn't know parser returns dicts, so we cast
            items_any: list[Any] = cast(list[Any], receipt_data.items)
            receipt_data.items = [item["name"] if isinstance(item, dict) else str(item) for item in items_any]

        # Log final results
        current_app.logger.debug("\n" + "=" * 60)
        current_app.logger.debug("FINAL EXTRACTED RECEIPT DATA:")
        current_app.logger.debug("=" * 60)
        current_app.logger.debug(f"  Amount: {receipt_data.amount}")
        current_app.logger.debug(f"  Total: {receipt_data.total}")
        current_app.logger.debug(f"  Tax: {receipt_data.tax}")
        current_app.logger.debug(f"  Tip: {receipt_data.tip}")
        current_app.logger.debug(f"  Date: {receipt_data.date}")
        current_app.logger.debug(f"  Time: {receipt_data.time}")
        current_app.logger.debug(f"  Restaurant: {receipt_data.restaurant_name}")
        current_app.logger.debug(f"  Address: {receipt_data.restaurant_address}")
        current_app.logger.debug(f"  Phone: {receipt_data.restaurant_phone}")
        current_app.logger.debug(f"  Website: {receipt_data.restaurant_website}")
        current_app.logger.debug(f"  Items: {len(receipt_data.items) if receipt_data.items else 0} items")
        current_app.logger.debug(f"  Confidence Scores: {receipt_data.confidence_scores}")
        current_app.logger.debug("=" * 60)

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
                current_app.logger.info(
                    f"Textract failed on PDF directly, attempting fallback: convert PDF to image for {filename}"
                )
                try:
                    return self._extract_text_from_pdf_via_image_fallback(file_bytes, filename)
                except Exception as fallback_error:
                    current_app.logger.error(f"PDF to image fallback also failed for {filename}: {fallback_error}")
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
        current_app.logger.debug(
            f"Calling AWS Textract detect_document_text for file: {filename} "
            f"({len(file_bytes)} bytes, PDF: {is_pdf})"
        )

        try:
            response = self.textract_client.detect_document_text(Document={"Bytes": file_bytes})
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            current_app.logger.error(f"AWS Textract API error ({error_code}): {error_message} for file: {filename}")

            if error_code == "InvalidParameterException":
                raise ValueError(f"Invalid document parameters. File: {filename}. " f"Error: {error_message}") from e

            # Re-raise to let caller handle fallback logic
            raise

        # Log response metadata for debugging
        if response.get("DocumentMetadata"):
            pages = response["DocumentMetadata"].get("Pages", 0)
            current_app.logger.debug(f"Textract processed {pages} page(s)")

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
        current_app.logger.debug(
            f"Extracted {len(raw_text)} characters from {len(text_lines)} lines using AWS Textract"
        )

        # Warn if no text was extracted
        if not raw_text or len(raw_text.strip()) < 10:
            current_app.logger.warning(
                f"Textract returned minimal or no text for {filename}. "
                f"This may indicate an unsupported PDF structure or encoding."
            )

        # Log confidence scores if available
        if response.get("Blocks"):
            line_blocks = [b for b in response["Blocks"] if b.get("BlockType") == "LINE"]
            if line_blocks:
                avg_confidence = sum(block.get("Confidence", 0) for block in line_blocks) / len(line_blocks)
                current_app.logger.debug(f"Average confidence: {avg_confidence:.2f}%")

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
        # Check if poppler is available (pdf2image requires it)
        self._verify_poppler_available()

        current_app.logger.debug(f"Converting PDF to image for fallback processing: {filename}")

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

            current_app.logger.debug(f"Converted PDF to PNG image: {img.size}, {len(img_bytes)} bytes")

            # Process the image with Textract (use direct method to prevent recursion)
            return self._extract_text_from_image_or_pdf(img_bytes, filename.replace(".pdf", ".png"), False)

        except Exception as e:
            current_app.logger.error(f"PDF to image conversion failed: {e}")
            raise RuntimeError(f"Failed to convert PDF to image: {e}") from e

    def _verify_poppler_available(self) -> None:
        """Verify that poppler-utils is installed and available.

        Raises:
            RuntimeError: If poppler is not available
        """
        try:
            import subprocess

            # Use full path to prevent PATH manipulation attacks (Bandit B607)
            pdftoppm_path = shutil.which("pdftoppm")
            if not pdftoppm_path:
                raise FileNotFoundError("pdftoppm not found in PATH")

            result = subprocess.run(
                [pdftoppm_path, "-v"],
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
            current_app.logger.warning(f"Could not verify poppler installation: {e}")


def get_ocr_service() -> OCRService | None:
    """Get OCR service instance.

    Returns:
        OCRService instance or None if OCR is disabled
    """
    try:
        return OCRService()
    except Exception as e:
        current_app.logger.error(f"Failed to initialize OCR service: {e}")
        return None
