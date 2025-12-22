"""OCR service for extracting data from receipt images using Tesseract OCR (FREE, open-source)."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
from typing import Any, cast

from flask import current_app
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from werkzeug.datastructures import FileStorage

fitz: Any = None
try:
    import fitz  # PyMuPDF
except ImportError:
    pass

# PyMuPDF is the primary PDF library (required dependency)
# pdf2image removed - PyMuPDF is faster, has no system dependencies, and handles embedded images better


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
    items: list[str] | None = None
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
    """Service for extracting text and data from receipt images using Tesseract OCR."""

    def __init__(self) -> None:
        """Initialize OCR service with configuration."""
        self.enabled = current_app.config.get("OCR_ENABLED", True)
        self.confidence_threshold = current_app.config.get("OCR_CONFIDENCE_THRESHOLD", 0.7)
        self.tesseract_cmd = current_app.config.get("TESSERACT_CMD")

        # Set Tesseract command path if provided
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

        # Verify Tesseract is available
        if self.enabled:
            try:
                pytesseract.get_tesseract_version()
                current_app.logger.info("Tesseract OCR initialized successfully")
            except pytesseract.TesseractNotFoundError:
                current_app.logger.error(
                    "Tesseract OCR binary not found. Please install it:\n"
                    "  Linux: sudo apt-get install tesseract-ocr\n"
                    "  macOS: brew install tesseract\n"
                    "  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki"
                )
                self.enabled = False
            except Exception as e:
                current_app.logger.warning(f"Tesseract OCR not available: {e}")
                self.enabled = False

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
                "OCR is disabled. Tesseract OCR binary is not installed. "
                "Please install Tesseract OCR:\n"
                "  Linux: sudo apt-get install tesseract-ocr\n"
                "  macOS: brew install tesseract\n"
                "  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki"
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

        # Try to extract text directly from PDF first (faster, more accurate)
        # Strategy: Try text extraction, if we get < 50 chars, assume it's image-based and use OCR
        raw_text = ""
        if is_pdf and fitz is not None:
            try:
                raw_text = self._extract_text_from_pdf_simple(file_bytes)
                if raw_text and len(raw_text.strip()) > 50:
                    current_app.logger.debug(f"Extracted {len(raw_text)} chars directly from PDF (no OCR needed)")
                else:
                    # Little or no text - likely image-based PDF, use OCR
                    current_app.logger.debug(
                        f"PDF text extraction returned {len(raw_text) if raw_text else 0} chars - using OCR"
                    )
                    raw_text = ""  # Fall through to OCR
            except Exception as e:
                current_app.logger.debug(f"PDF text extraction failed, falling back to OCR: {e}")
                raw_text = ""

        # If no text extracted directly, use OCR (for images or scanned PDFs)
        if not raw_text or len(raw_text.strip()) < 10:
            # Preprocess image/PDF
            try:
                processed_image = self._preprocess_image(file_bytes, file_storage.filename)
            except Exception as e:
                current_app.logger.error(f"Image preprocessing failed: {e}")
                raise RuntimeError(f"Failed to preprocess image: {e}") from e

            # Detect if this might be a bank statement before OCR (for better config)
            # Quick check: look for bank keywords in filename
            is_likely_bank_statement = False
            if file_storage.filename:
                filename_lower = file_storage.filename.lower()
                bank_indicators = ["statement", "bank", "account", "transaction"]
                is_likely_bank_statement = any(indicator in filename_lower for indicator in bank_indicators)

            # Extract text using Tesseract OCR with appropriate config
            try:
                raw_text = self._extract_text_with_tesseract(
                    processed_image, is_bank_statement=is_likely_bank_statement
                )
            except Exception as e:
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

    def _extract_text_from_pdf_simple(self, pdf_bytes: bytes) -> str:
        """Extract text directly from PDF if it has a text layer.

        Simple version - assumes PDF has no embedded images (checked separately).

        Args:
            pdf_bytes: Raw PDF file bytes

        Returns:
            Extracted text string, or empty string if extraction fails
        """
        if fitz is None:
            return ""

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text_parts = []

            # Extract text from first page (receipts are typically single page)
            if len(doc) > 0:
                page = doc[0]
                text = page.get_text()
                if text:
                    text_parts.append(text.strip())

            doc.close()

            result = "\n".join(text_parts)
            current_app.logger.debug(f"Extracted {len(result)} characters directly from PDF")
            return result
        except Exception as e:
            current_app.logger.warning(f"PDF text extraction failed: {e}")
            return ""

    def _preprocess_image(self, image_bytes: bytes, filename: str) -> Image.Image:
        """Preprocess image to improve OCR accuracy.

        Args:
            image_bytes: Raw image bytes
            filename: Original filename (for format detection)

        Returns:
            Preprocessed PIL Image

        Raises:
            ValueError: If file format is not supported
            RuntimeError: If PDF conversion fails
        """
        # Check if file is a PDF
        is_pdf = filename.lower().endswith(".pdf") or image_bytes[:4] == b"%PDF"

        if is_pdf:
            # Use PyMuPDF (required dependency - faster, no system deps, handles embedded images better)
            if fitz is None:
                raise RuntimeError("PDF processing requires PyMuPDF library. " "Install with: pip install PyMuPDF")
            try:
                doc = fitz.open(stream=image_bytes, filetype="pdf")
                if len(doc) > 0:
                    page = doc[0]

                    # Check for embedded images for debugging
                    image_list = page.get_images()
                    current_app.logger.debug(f"PDF page has {len(image_list)} embedded images")

                    # Render page as image at 300 DPI for better OCR accuracy
                    # get_pixmap() renders the entire page including embedded images
                    # Use higher DPI (300) for better OCR accuracy on scanned PDFs
                    zoom = 300 / 72  # 300 DPI
                    mat = fitz.Matrix(zoom, zoom)

                    # Render the page - this includes all embedded images
                    pix = page.get_pixmap(matrix=mat, alpha=False, annots=True)

                    # Verify we got a valid image
                    if pix.width == 0 or pix.height == 0:
                        raise ValueError(f"PDF rendered to invalid size: {pix.width}x{pix.height}")

                    # Convert to PIL Image
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

                    # Free memory
                    pix = None
                    doc.close()

                    # Verify image has content (not blank/white)
                    # Simple check: count non-white pixels (RGB > 240,240,240)
                    non_white_pixels = sum(1 for pixel in img.getdata() if not all(c > 240 for c in pixel))
                    total_pixels = img.width * img.height
                    white_ratio = 1.0 - (non_white_pixels / total_pixels) if total_pixels > 0 else 0
                    if white_ratio > 0.95:  # More than 95% white
                        current_app.logger.warning(
                            f"Rendered PDF image appears mostly white ({white_ratio*100:.1f}% white) - "
                            "may indicate rendering issue or blank page"
                        )

                    current_app.logger.debug(
                        f"Converted PDF page to image using PyMuPDF: {img.size} "
                        f"(300 DPI, {len(image_list)} embedded images)"
                    )
                else:
                    raise ValueError("PDF has no pages")
            except Exception as e:
                current_app.logger.error(f"PyMuPDF PDF conversion failed: {e}")
                raise RuntimeError(f"Failed to convert PDF to image: {e}") from e
        else:
            # Open image from bytes
            try:
                img = cast(Image.Image, Image.open(BytesIO(image_bytes)))
            except Exception as e:
                current_app.logger.error(f"Failed to open image: {e}")
                raise ValueError(f"Unsupported image format: {e}") from e

        # Convert to RGB if necessary (handles RGBA, P, etc.)
        if img.mode != "RGB":
            img = cast(Image.Image, img.convert("RGB"))

        # Resize if image is too large (improves OCR speed and accuracy)
        max_size = 2000
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = cast(Image.Image, img.resize(new_size, Image.Resampling.LANCZOS))
            current_app.logger.debug(f"Resized image from {img.size} to {new_size}")

        # Convert to grayscale
        img = cast(Image.Image, img.convert("L"))

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = cast(Image.Image, enhancer.enhance(1.5))

        # Apply slight sharpening
        img = cast(Image.Image, img.filter(ImageFilter.SHARPEN))

        return cast(Image.Image, img)

    def _extract_text_with_tesseract(self, image: Image.Image, is_bank_statement: bool = False) -> str:
        """Extract text from image using Tesseract OCR.

        Args:
            image: Preprocessed PIL Image
            is_bank_statement: Whether this is a bank statement (uses different PSM mode)

        Returns:
            Extracted text string
        """
        # Configure Tesseract for better recognition
        # PSM 6 = Assume uniform block of text (good for receipts)
        # PSM 4 = Assume single column of text (better for bank statements)
        # PSM 11 = Sparse text (good for tabular data)
        if is_bank_statement:
            # Try multiple PSM modes for bank statements to get best results
            configs = [
                r"--oem 3 --psm 11",  # Sparse text (tabular data)
                r"--oem 3 --psm 4",  # Single column
                r"--oem 3 --psm 6",  # Uniform block
            ]
        else:
            configs = [r"--oem 3 --psm 6"]  # Uniform block for receipts

        best_text = ""
        best_length = 0

        for config in configs:
            try:
                text = cast(str, pytesseract.image_to_string(image, config=config))
                # Prefer longer text (more complete extraction)
                if len(text) > best_length:
                    best_text = text
                    best_length = len(text)
            except Exception as e:
                current_app.logger.debug(f"Tesseract OCR config {config} failed: {e}")
                continue

        if not best_text:
            raise RuntimeError("Tesseract OCR failed with all configurations")

        current_app.logger.debug(f"Extracted {len(best_text)} characters using OCR")
        return best_text

    def _parse_receipt_data(
        self,
        raw_text: str,
        form_hints: dict[str, Any] | None = None,
    ) -> ReceiptData:
        """Parse receipt data from extracted text.

        Args:
            raw_text: Raw text extracted from OCR
            form_hints: Optional dictionary with form values to use as hints for matching

        Returns:
            ReceiptData object with parsed fields
        """
        receipt_data = ReceiptData(raw_text=raw_text)
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

        # Log ALL lines for debugging
        current_app.logger.debug("=" * 60)
        current_app.logger.debug("ALL LINES FROM OCR TEXT:")
        current_app.logger.debug("=" * 60)
        current_app.logger.debug(f"Total lines found: {len(lines)}")
        for i, line in enumerate(lines, 1):
            current_app.logger.debug(f"  Line {i}: {line}")
        current_app.logger.debug("=" * 60)

        if not lines:
            current_app.logger.warning("No lines found in OCR text - returning empty ReceiptData")
            return receipt_data

        # Detect if this is a bank statement vs receipt
        is_bank_statement = self._is_bank_statement(raw_text, lines)

        if is_bank_statement:
            current_app.logger.debug("Detected bank statement format")
            return self._parse_bank_statement(raw_text, lines, form_hints=form_hints)

        # Standard receipt parsing
        # Extract restaurant name (usually first or second line)
        name_result = self._extract_restaurant_name(lines)
        receipt_data.restaurant_name, receipt_data.restaurant_location_number = name_result
        current_app.logger.debug(f"Extracted restaurant name: {receipt_data.restaurant_name}")
        if receipt_data.restaurant_location_number:
            current_app.logger.debug(f"Extracted restaurant location number: {receipt_data.restaurant_location_number}")

        # Extract restaurant address
        receipt_data.restaurant_address = self._extract_restaurant_address(lines)
        current_app.logger.debug(f"Extracted restaurant address: {receipt_data.restaurant_address}")

        # Extract restaurant phone (try lines first, then fallback to raw text)
        receipt_data.restaurant_phone = self._extract_restaurant_phone(lines)
        if not receipt_data.restaurant_phone:
            # Fallback: search raw text directly (handles phone numbers split across lines)
            receipt_data.restaurant_phone = self._extract_restaurant_phone_from_text(raw_text)
        current_app.logger.debug(f"Extracted restaurant phone: {receipt_data.restaurant_phone}")

        # Extract restaurant website
        receipt_data.restaurant_website = self._extract_restaurant_website(lines)
        current_app.logger.debug(f"Extracted restaurant website: {receipt_data.restaurant_website}")

        # Extract date and time
        receipt_data.date = self._extract_date(raw_text)
        receipt_data.time = self._extract_time(raw_text, lines)
        current_app.logger.debug(f"Extracted date: {receipt_data.date}")
        current_app.logger.debug(f"Extracted time: {receipt_data.time}")

        # Extract amounts (total, tax, tip, subtotal) - improved extraction
        amounts = self._extract_amounts(raw_text, lines)

        # Use form hints to improve amount matching if provided
        if form_hints and form_hints.get("amount"):
            try:
                expected_amount = Decimal(str(form_hints["amount"]))
                # If we found amounts, pick the one closest to expected
                found_amounts = [v for v in amounts.values() if v is not None]
                if found_amounts:
                    closest = min(found_amounts, key=lambda x: abs(x - expected_amount))
                    # If close match (within $5), use it
                    if abs(closest - expected_amount) <= Decimal("5.00"):
                        receipt_data.total = closest
                        receipt_data.amount = closest
                    else:
                        # Use extracted amounts as-is
                        receipt_data.total = amounts.get("total")
                        receipt_data.amount = receipt_data.total or amounts.get("subtotal")
                else:
                    # No amounts found, use expected from form
                    receipt_data.total = expected_amount
                    receipt_data.amount = expected_amount
            except (InvalidOperation, ValueError):
                # Fallback to extracted amounts
                receipt_data.total = amounts.get("total")
                receipt_data.amount = receipt_data.total or amounts.get("subtotal")
        else:
            # No form hints, use extracted amounts
            receipt_data.total = amounts.get("total")
            receipt_data.amount = receipt_data.total or amounts.get("subtotal")
            current_app.logger.debug(f"Assigned from amounts: total={receipt_data.total}, amount={receipt_data.amount}")

        receipt_data.tax = amounts.get("tax")
        receipt_data.tip = amounts.get("tip")
        current_app.logger.debug(
            f"Final assignment: total={receipt_data.total}, tax={receipt_data.tax}, amount={receipt_data.amount}"
        )

        # Extract line items
        receipt_data.items = self._extract_items(lines)
        current_app.logger.debug(f"Extracted {len(receipt_data.items)} line items: {receipt_data.items[:5]}")

        # Calculate confidence scores (simplified - based on successful extraction)
        receipt_data.confidence_scores = self._calculate_confidence_scores(receipt_data)

        # Final summary log
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
        current_app.logger.debug(f"  Items: {len(receipt_data.items)} items")
        current_app.logger.debug(f"  Confidence Scores: {receipt_data.confidence_scores}")
        current_app.logger.debug("=" * 60)

        return receipt_data

    def _extract_restaurant_name(self, lines: list[str]) -> tuple[str | None, str | None]:
        """Extract restaurant name from receipt lines.

        Args:
            lines: List of text lines from receipt

        Returns:
            Tuple of (restaurant name, location number) or (None, None)
        """
        if not lines:
            return None, None

        # Skip email headers and common receipt words
        skip_words = {
            "receipt",
            "invoice",
            "thank",
            "you",
            "visit",
            "us",
            "again",
            "outlook",
            "gmail",
            "yahoo",
            "hotmail",
            "from",
            "to",
            "date",
            "subject",
            "sent",
            "reply",
            "no-reply",
            "order",
            "check",
        }

        # Patterns to exclude (times, dates, amounts, email addresses, addresses, etc.)
        exclude_patterns = [
            r"^\d{1,2}:\d{2}\s*(AM|PM|am|pm)$",  # Time: "12:55 PM"
            r"^\d{1,2}:\d{2}$",  # Time without AM/PM: "12:55"
            r"^\d+[\s\d:/-]*$",  # Just numbers with separators
            r"^\$?\s*\d+\.\d{2}$",  # Just an amount: "$10.00"
            r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$",  # Date: "10/05/2025"
            r"^\d{4}[/-]\d{1,2}[/-]\d{1,2}$",  # Date: "2025-10-05"
            r"^total|tax|tip|subtotal",  # Common receipt labels
            r"^\d+\s*x\s*\$?\d+",  # Quantity x price
            r"^table\s+\d+|server\s+\d+|check\s+\d+",  # Table/server/check numbers
            r".*@.*",  # Email addresses
            r"^from\s+|^to\s+|^subject\s+",  # Email headers
            r"^\d+\s+[A-Z]\s+FM\s+\d+",  # Address pattern: "3300 W FM 544"
            r"^\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Circle|Cir|Place|Pl|FM)\s*\d*",  # Street addresses
            r"^[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}",  # City, State ZIP (address line)
        ]

        # Restaurant name indicators (prioritize lines with these)
        restaurant_indicators = [
            "bros",
            "restaurant",
            "cafe",
            "grill",
            "diner",
            "kitchen",
            "pizza",
            "bar",
            "tavern",
            "bistro",
            "eatery",
            "deli",
        ]

        # Check more lines (up to 10) to find restaurant name past email headers
        for line in lines[:10]:
            line_lower = line.lower().strip()
            line_stripped = line.strip()

            # Skip empty lines
            if not line_stripped or len(line_stripped) < 3:
                continue

            # Skip lines with skip words (email clients, headers, etc.)
            # Use word boundaries to avoid false positives (e.g., "to" matching "COTTON")
            line_words = set(re.findall(r"\b\w+\b", line_lower))
            skip_words_set = set(skip_words)
            if line_words & skip_words_set:  # Check for whole word matches only
                matched_words = line_words & skip_words_set
                current_app.logger.debug(f"Skipping line '{line_stripped}' (contains skip word: {matched_words})")
                continue

            # Skip lines matching exclude patterns
            if any(re.match(pattern, line_stripped, re.IGNORECASE) for pattern in exclude_patterns):
                current_app.logger.debug(f"Skipping line '{line_stripped}' (matches exclude pattern)")
                continue

            # Skip lines that are mostly numbers or amounts
            if re.search(r"^\$?\s*\d+\.\d{2}", line_stripped) and len(re.sub(r"[\d\s\$\.]", "", line_stripped)) < 3:
                current_app.logger.debug(f"Skipping line '{line_stripped}' (mostly numbers/amount)")
                continue

            # Must have at least some letters (restaurant names have letters)
            if not re.search(r"[a-zA-Z]{2,}", line_stripped):
                current_app.logger.debug(f"Skipping line '{line_stripped}' (no letters found)")
                continue

            # Skip lines that look like addresses (street addresses, city/state/zip)
            # Check for address patterns: starts with number + street type, or city/state/zip pattern
            if re.match(r"^\d+\s+[A-Z]\s+FM\s+\d+", line_stripped, re.IGNORECASE):
                current_app.logger.debug(f"Skipping line '{line_stripped}' (address pattern: FM road)")
                continue
            if re.match(
                r"^\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Circle|Cir|Place|Pl|FM)\s*\d*",
                line_stripped,
                re.IGNORECASE,
            ):
                current_app.logger.debug(f"Skipping line '{line_stripped}' (address pattern: street address)")
                continue
            if re.match(r"^[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}", line_stripped):
                current_app.logger.debug(f"Skipping line '{line_stripped}' (address pattern: city/state/zip)")
                continue

            # Clean up common receipt artifacts
            name = re.sub(r"^\W+|\W+$", "", line_stripped)  # Remove leading/trailing punctuation
            name = re.sub(r"\s+", " ", name).strip()  # Normalize whitespace

            # Extract location/store number before removing it
            location_number = None
            location_patterns = [
                r"\s*#\s*(\d+)\s*$",  # "#41" or " #41"
                r"\s*[-–—]\s*#\s*(\d+)\s*$",  # " - #41" or " – #41"
                r"\s+#\s*(\d+)\s*$",  # " #41"
                r"\s+(\d{2,4})\s*$",  # " 0033" or " 41" (2-4 digits, likely location number)
            ]
            for pattern in location_patterns:
                match = re.search(pattern, name, re.IGNORECASE)
                if match:
                    matched_number = match.group(1)
                    # Check if it's a location number pattern (not a zip code or year)
                    # Location numbers are typically 2-4 digits, not 5 digits (zip codes)
                    # and not years (1900-2100 range)
                    if len(matched_number) <= 4:
                        try:
                            num_val = int(matched_number)
                            # Skip if it looks like a year (1900-2100)
                            if 1900 <= num_val <= 2100:
                                continue
                            # Skip if it's a single digit (likely not a location number)
                            if len(matched_number) == 1:
                                continue
                            # Use "#" prefix if pattern had "#", otherwise use as-is
                            if "#" in pattern:
                                location_number = f"#{matched_number}"
                            else:
                                location_number = matched_number
                            break
                        except ValueError:
                            continue

            # Remove location numbers like "#41", "#123", "0033", etc. at the end
            name = re.sub(r"\s*#\s*\d+\s*$", "", name, flags=re.IGNORECASE)
            name = re.sub(r"\s*[-–—]\s*#\s*\d+\s*$", "", name, flags=re.IGNORECASE)
            name = re.sub(r"\s+#\s*\d+\s*$", "", name, flags=re.IGNORECASE)
            # Remove trailing numbers (2-4 digits) that could be location numbers
            # But be careful not to remove years or zip codes
            trailing_num_match = re.search(r"\s+(\d{2,4})\s*$", name)
            if trailing_num_match:
                num_str = trailing_num_match.group(1)
                try:
                    num_val = int(num_str)
                    # Only remove if it's not a year (1900-2100) and not a zip code (5 digits)
                    if not (1900 <= num_val <= 2100) and len(num_str) <= 4:
                        name = re.sub(r"\s+\d{2,4}\s*$", "", name)
                except ValueError:
                    pass

            # Clean up any trailing dashes or spaces left after removal
            name = re.sub(r"\s*[-–—]\s*$", "", name)
            name = name.strip()

            # Check if this looks like a restaurant name
            has_restaurant_indicator = any(indicator in line_lower for indicator in restaurant_indicators)

            # If it has restaurant indicators, prioritize it
            if len(name) > 2:
                if has_restaurant_indicator:
                    current_app.logger.debug(
                        f"Extracted restaurant name (with indicator): '{name}' from line '{line_stripped}'"
                    )
                    if location_number:
                        current_app.logger.debug(f"Extracted location number: '{location_number}'")
                    return name, location_number
                # Otherwise, continue searching for one with indicators

        # If no restaurant indicator found, return the first valid name found
        for line in lines[:10]:
            line_lower = line.lower().strip()
            line_stripped = line.strip()

            if not line_stripped or len(line_stripped) < 3:
                continue

            # Use word boundaries to avoid false positives
            line_words = set(re.findall(r"\b\w+\b", line_lower))
            skip_words_set = set(skip_words)
            if line_words & skip_words_set:  # Check for whole word matches only
                continue

            if any(re.match(pattern, line_stripped, re.IGNORECASE) for pattern in exclude_patterns):
                continue

            if re.search(r"^\$?\s*\d+\.\d{2}", line_stripped) and len(re.sub(r"[\d\s\$\.]", "", line_stripped)) < 3:
                continue

            if not re.search(r"[a-zA-Z]{2,}", line_stripped):
                continue

            # Skip lines that look like addresses in fallback too
            if re.match(r"^\d+\s+[A-Z]\s+FM\s+\d+", line_stripped, re.IGNORECASE):
                current_app.logger.debug(f"Skipping line '{line_stripped}' (fallback: address pattern: FM road)")
                continue
            if re.match(
                r"^\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Circle|Cir|Place|Pl|FM)\s*\d*",
                line_stripped,
                re.IGNORECASE,
            ):
                current_app.logger.debug(f"Skipping line '{line_stripped}' (fallback: address pattern: street address)")
                continue
            if re.match(r"^[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}", line_stripped):
                current_app.logger.debug(f"Skipping line '{line_stripped}' (fallback: address pattern: city/state/zip)")
                continue

            name = re.sub(r"^\W+|\W+$", "", line_stripped)
            name = re.sub(r"\s+", " ", name).strip()

            # Extract location/store number before removing it
            location_number = None
            location_patterns = [
                r"\s*#\s*(\d+)\s*$",  # "#41" or " #41"
                r"\s*[-–—]\s*#\s*(\d+)\s*$",  # " - #41" or " – #41"
                r"\s+#\s*(\d+)\s*$",  # " #41"
                r"\s+(\d{2,4})\s*$",  # " 0033" or " 41" (2-4 digits, likely location number)
            ]
            for pattern in location_patterns:
                match = re.search(pattern, name, re.IGNORECASE)
                if match:
                    matched_number = match.group(1)
                    # Check if it's a location number pattern (not a zip code or year)
                    # Location numbers are typically 2-4 digits, not 5 digits (zip codes)
                    # and not years (1900-2100 range)
                    if len(matched_number) <= 4:
                        try:
                            num_val = int(matched_number)
                            # Skip if it looks like a year (1900-2100)
                            if 1900 <= num_val <= 2100:
                                continue
                            # Skip if it's a single digit (likely not a location number)
                            if len(matched_number) == 1:
                                continue
                            # Use "#" prefix if pattern had "#", otherwise use as-is
                            if "#" in pattern:
                                location_number = f"#{matched_number}"
                            else:
                                location_number = matched_number
                            break
                        except ValueError:
                            continue

            # Remove location numbers like "#41", "#123", "0033", etc. at the end
            name = re.sub(r"\s*#\s*\d+\s*$", "", name, flags=re.IGNORECASE)
            name = re.sub(r"\s*[-–—]\s*#\s*\d+\s*$", "", name, flags=re.IGNORECASE)
            name = re.sub(r"\s+#\s*\d+\s*$", "", name, flags=re.IGNORECASE)
            # Remove trailing numbers (2-4 digits) that could be location numbers
            # But be careful not to remove years or zip codes
            trailing_num_match = re.search(r"\s+(\d{2,4})\s*$", name)
            if trailing_num_match:
                num_str = trailing_num_match.group(1)
                try:
                    num_val = int(num_str)
                    # Only remove if it's not a year (1900-2100) and not a zip code (5 digits)
                    if not (1900 <= num_val <= 2100) and len(num_str) <= 4:
                        name = re.sub(r"\s+\d{2,4}\s*$", "", name)
                except ValueError:
                    pass

            # Clean up any trailing dashes or spaces left after removal
            name = re.sub(r"\s*[-–—]\s*$", "", name)
            name = name.strip()

            if len(name) > 2:
                current_app.logger.debug(f"Extracted restaurant name (fallback): '{name}' from line '{line_stripped}'")
                if location_number:
                    current_app.logger.debug(f"Extracted location number (fallback): '{location_number}'")
                return name, location_number

        current_app.logger.debug("No restaurant name found in first 10 lines")
        return None, None

    def _extract_restaurant_address(self, lines: list[str]) -> str | None:
        """Extract restaurant address from receipt lines.

        Addresses are typically found after the restaurant name, usually within
        the first 10-15 lines of a receipt. Stops when menu items are detected.

        Args:
            lines: List of text lines from receipt

        Returns:
            Restaurant address string or None
        """
        if not lines:
            return None

        # Skip email headers and common receipt words
        skip_words = {
            "receipt",
            "invoice",
            "thank",
            "you",
            "visit",
            "us",
            "again",
            "outlook",
            "gmail",
            "yahoo",
            "hotmail",
            "from",
            "to",
            "date",
            "subject",
            "sent",
            "reply",
            "no-reply",
            "order",
            "check",
            "phone",
            "tel",
            "call",
            "email",
            "web",
            "www",
        }

        # Menu item indicators - if we see these, we've moved past the address section
        menu_item_indicators = [
            r"^\s*[A-Z][a-z]+(?:\s+-\s+[A-Z][a-z]+)+",  # "Classic - Mixed Plate" pattern
            r"^\s*[A-Z][a-z]+\s+-\s+[A-Z]",  # "Item - Description" pattern
            r"^\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+-\s+[A-Z]",  # Multi-word items with dash
        ]

        # Patterns to identify address lines
        # Address patterns: street number + street name, or city/state/zip
        address_patterns = [
            r"\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Circle|Cir|Place|Pl)",  # Street address
            r"\d+\s+[A-Z]\s+FM\s+\d+",  # Farm to Market Road pattern: "3300 W FM 544"
            r"\d+\s+[A-Za-z\s]+FM\s+\d+",  # FM Road pattern without directional
            r"\d+\s+[A-Za-z0-9\s]+",  # Number + words/numbers (potential street address, includes numbered routes)
            r"[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?",  # City, State ZIP
            r"[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*[A-Z]{2}",  # City, State
            r"\d{5}(?:-\d{4})?",  # ZIP code
        ]

        # Look for address in lines after restaurant name (typically lines 2-15)
        # Addresses usually appear within a few lines of the restaurant name
        address_lines: list[str] = []
        found_complete_address = False  # Track if we found city/state/zip

        for idx, line in enumerate(lines[:20]):  # Check first 20 lines
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            # Skip empty lines
            if not line_stripped or len(line_stripped) < 5:
                current_app.logger.debug(f"Skipping line {idx} (empty or too short): '{line_stripped}'")
                continue

            # Skip lines with skip words
            skip_word_found = any(word in line_lower for word in skip_words)
            if skip_word_found:
                current_app.logger.debug(f"Skipping line {idx} (contains skip word): '{line_stripped}'")
                continue

            # Skip time patterns
            if re.match(r"^\d{1,2}:\d{2}\s*(AM|PM|am|pm)?$", line_stripped, re.IGNORECASE):
                continue

            # Skip date patterns (MM/DD/YY, MM/DD/YYYY, etc.)
            if re.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$", line_stripped):
                continue

            # Extract address part before date/time if present
            date_time_match = re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+\d{1,2}:\d{2}", line_stripped)
            if date_time_match:
                address_part = line_stripped[: date_time_match.start()].strip()
                if len(address_part) >= 5:
                    line_stripped = address_part
                else:
                    continue

            # Skip email addresses
            if "@" in line_stripped:
                continue

            # Skip lines that are just amounts
            if re.match(r"^\$?\s*\d+\.\d{2}$", line_stripped):
                continue

            # Check if this looks like a menu item (stop collecting address if so)
            is_menu_item = False

            # Check for menu item patterns: lines with "1x", "2x", etc. followed by item name
            if re.match(r"^\d+x\s+[A-Z]", line_stripped, re.IGNORECASE):
                is_menu_item = True
                current_app.logger.debug(
                    f"Stopping address extraction at line {idx} (menu item with quantity): '{line_stripped}'"
                )

            # Check for lines with amounts at the end (menu items with prices)
            if not is_menu_item and re.search(r"\$\d+\.\d{2}\s*$", line_stripped):
                # But exclude if it's clearly an address (has state abbreviation and zip)
                if not re.search(r"[A-Z]{2}\s+\d{5}", line_stripped):
                    is_menu_item = True
                    current_app.logger.debug(
                        f"Stopping address extraction at line {idx} (menu item with price): '{line_stripped}'"
                    )

            # Check menu item indicator patterns
            if not is_menu_item:
                for pattern in menu_item_indicators:
                    if re.match(pattern, line_stripped):
                        is_menu_item = True
                        current_app.logger.debug(
                            f"Stopping address extraction at line {idx} (menu item detected): '{line_stripped}'"
                        )
                        break

            # Also check for common menu item patterns
            if not is_menu_item:
                # Lines with dashes that look like menu items (e.g., "Classic - Mixed Plate")
                if re.search(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+-\s+[A-Z]", line_stripped):
                    # But exclude if it's clearly an address (has state abbreviation and zip)
                    if not re.search(r"[A-Z]{2}\s+\d{5}", line_stripped):
                        is_menu_item = True
                        current_app.logger.debug(
                            f"Stopping address extraction at line {idx} (menu item pattern): '{line_stripped}'"
                        )

            # If we found a complete address (city, state, zip), stop collecting more lines
            if found_complete_address:
                # Only stop if we see a menu item after finding complete address
                if is_menu_item:
                    break
                # Also stop if we've collected enough lines (2 lines before city/state/zip)
                if address_lines:
                    city_state_zip_idx = None
                    for i, addr_line in enumerate(address_lines):
                        if re.search(r"[A-Z]{2}\s+\d{5}", addr_line):
                            city_state_zip_idx = i
                            break
                    if city_state_zip_idx is not None and idx > city_state_zip_idx:
                        break

            # If we've already collected address lines and see a menu item, stop
            if address_lines and is_menu_item:
                break

            # Check if this looks like an address line
            is_address_line = False
            for pattern in address_patterns:
                if re.search(pattern, line_stripped, re.IGNORECASE):
                    is_address_line = True
                    break

            # Also check for common address indicators
            address_indicators = [
                "street",
                "st",
                "avenue",
                "ave",
                "road",
                "rd",
                "boulevard",
                "blvd",
                "drive",
                "dr",
                "lane",
                "ln",
                "court",
                "ct",
                "way",
                "circle",
                "cir",
                "place",
                "pl",
                "suite",
                "ste",
                "unit",
                "apt",
                "apartment",
                "fm",  # Farm to Market Road abbreviation
            ]

            # Check for FM (Farm to Market Road) pattern specifically
            if not is_address_line:
                if re.search(r"\bFM\s+\d+\b", line_stripped, re.IGNORECASE):
                    # Check if it's preceded by a number (street number) and optional directional
                    if re.search(r"\d+\s+[A-Z]?\s*FM\s+\d+", line_stripped, re.IGNORECASE):
                        is_address_line = True
                        current_app.logger.debug(f"Found FM address pattern at line {idx}: '{line_stripped}'")

            if not is_address_line:
                # Check if line contains address indicators (including "fm")
                if any(indicator in line_lower for indicator in address_indicators):
                    is_address_line = True
                    if "fm" in line_lower:
                        current_app.logger.debug(f"Found address via FM indicator at line {idx}: '{line_stripped}'")

            # Check for city/state/zip pattern (complete address)
            if not is_address_line:
                # Pattern: City, State ZIP or City State ZIP
                if re.search(r"[A-Za-z\s]{3,},\s*[A-Z]{2}\s+\d{5}", line_stripped):
                    is_address_line = True
                    found_complete_address = True
                elif re.search(r"[A-Za-z\s]{3,}\s+[A-Z]{2}\s+\d{5}", line_stripped):
                    is_address_line = True
                    found_complete_address = True

            if is_address_line:
                address_lines.append(line_stripped)
                current_app.logger.debug(f"Found address line {idx}: '{line_stripped}'")

        # Combine address lines (at most 2 lines before city/state/zip, or 3 total)
        if address_lines:
            # Find the line with city/state/zip if present
            city_state_zip_idx = None
            for i, addr_line in enumerate(address_lines):
                if re.search(r"[A-Z]{2}\s+\d{5}", addr_line):
                    city_state_zip_idx = i
                    break

            if city_state_zip_idx is not None:
                # Found city/state/zip - take up to 2 lines before it, plus the city/state/zip line
                max_lines = city_state_zip_idx + 1
            else:
                # No city/state/zip found - take at most 2 lines
                max_lines = min(2, len(address_lines))

            combined_address = " ".join(address_lines[:max_lines])
            # Clean up extra whitespace
            combined_address = re.sub(r"\s+", " ", combined_address).strip()
            current_app.logger.debug(f"Extracted restaurant address: '{combined_address}'")
            return combined_address

        current_app.logger.debug("No restaurant address found in first 20 lines")
        return None

    def _extract_restaurant_phone(self, lines: list[str]) -> str | None:
        """Extract restaurant phone number from receipt lines.

        Phone numbers are typically found near the restaurant name and address,
        usually within the first 10-15 lines of a receipt.

        Args:
            lines: List of text lines from receipt

        Returns:
            Restaurant phone number string or None
        """
        if not lines:
            return None

        # Phone number patterns (various formats) - more flexible patterns
        phone_patterns = [
            r"\(?\d{3}\)?\s*-?\s*\d{3}\s*-?\s*\d{4}",  # (XXX) XXX-XXXX or XXX-XXX-XXXX
            r"\d{3}\.\d{3}\.\d{4}",  # XXX.XXX.XXXX
            r"\d{3}\s+\d{3}\s+\d{4}",  # XXX XXX XXXX
            r"\d{3}-\d{3}-\d{4}",  # XXX-XXX-XXXX (explicit dashes)
            r"\d{3}\.\d{3}\.\d{4}",  # XXX.XXX.XXXX (dots)
            r"\(\d{3}\)\s*\d{3}-\d{4}",  # (XXX) XXX-XXXX
            r"\(\d{3}\)\s*\d{3}\.\d{4}",  # (XXX) XXX.XXXX
            r"\d{10}",  # XXXXXXXXXX (10 digits) - check this last to avoid false positives
        ]

        # Skip words that indicate non-phone lines (but NOT phone-related words)
        skip_words = {
            "receipt",
            "invoice",
            "thank",
            "you",
            "visit",
            "us",
            "again",
            "outlook",
            "gmail",
            "yahoo",
            "hotmail",
            "from",
            "to",
            "date",
            "subject",
            "sent",
            "reply",
            "no-reply",
            "order",
            "check",
        }

        # Look for phone number in first 20 lines
        for idx, line in enumerate(lines[:20]):
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            # Skip empty lines (but allow shorter lines for phone numbers)
            if not line_stripped or len(line_stripped) < 7:
                continue

            # FIRST: Try to find phone pattern - if found, extract it regardless of skip words
            # This prioritizes phone number detection
            for pattern_idx, pattern in enumerate(phone_patterns):
                match = re.search(pattern, line_stripped)
                if match:
                    phone = match.group(0).strip()
                    # Extract all digits from the match
                    digits_only = re.sub(r"\D", "", phone)

                    # Skip if it's clearly not a phone number
                    # - All same digits (e.g., 0000000000, 1111111111)
                    if len(set(digits_only)) <= 2:
                        current_app.logger.debug(
                            f"Skipping phone-like pattern (all same digits): '{phone}' from line {idx}"
                        )
                        continue

                    # - If it's the 10-digit pattern and looks like a date or amount
                    if pattern_idx == len(phone_patterns) - 1:  # Last pattern (10 digits)
                        # Check if it's part of a date pattern (e.g., 10/05/2025)
                        if re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}", line_stripped):
                            continue
                        # Check if it's part of an amount (has $ or .XX pattern nearby)
                        if re.search(r"\$\s*\d+\.\d{2}", line_stripped) or re.search(r"\d+\.\d{2}", line_stripped):
                            # Only skip if the 10 digits are part of the amount
                            amount_match = re.search(r"(\d+)\.(\d{2})", line_stripped)
                            if amount_match and digits_only in amount_match.group(0):
                                continue

                    # Validate: should have 10 digits (US phone number)
                    # Also check for 11 digits starting with 1 (country code)
                    if len(digits_only) == 10:
                        # Additional validation: area code shouldn't start with 0 or 1
                        if digits_only[0] in ["0", "1"]:
                            current_app.logger.debug(
                                f"Skipping phone-like pattern (invalid area code): '{phone}' from line {idx}"
                            )
                            continue
                        # Format as (XXX) XXX-XXXX for consistency
                        formatted_phone = f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
                        current_app.logger.debug(
                            f"Extracted restaurant phone: '{formatted_phone}' from line {idx}: '{line_stripped}'"
                        )
                        return formatted_phone
                    elif len(digits_only) == 11 and digits_only[0] == "1":
                        # US number with country code - remove leading 1
                        digits_only = digits_only[1:]
                        # Validate area code
                        if digits_only[0] in ["0", "1"]:
                            current_app.logger.debug(
                                f"Skipping phone-like pattern (invalid area code): '{phone}' from line {idx}"
                            )
                            continue
                        formatted_phone = f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
                        current_app.logger.debug(
                            f"Extracted restaurant phone (with country code): '{formatted_phone}' from line {idx}: '{line_stripped}'"
                        )
                        return formatted_phone

            # SECOND: If no phone pattern found, apply skip filters
            # Skip lines with skip words (but allow lines with phone-related keywords)
            phone_keywords = ["phone", "tel", "call", "contact"]
            has_phone_keyword = any(keyword in line_lower for keyword in phone_keywords)

            if not has_phone_keyword:
                # Only skip if it doesn't have phone keywords
                if any(word in line_lower for word in skip_words):
                    continue

            # Skip lines that are just amounts
            if re.match(r"^\$?\s*\d+\.\d{2}$", line_stripped):
                continue

            # Skip date patterns (but not if they're part of a phone number)
            if re.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$", line_stripped):
                continue

            # Skip time patterns
            if re.match(r"^\d{1,2}:\d{2}\s*(AM|PM|am|pm)?$", line_stripped, re.IGNORECASE):
                continue

        current_app.logger.debug("No restaurant phone found in first 30 lines")
        return None

    def _extract_restaurant_phone_from_text(self, text: str) -> str | None:
        """Extract restaurant phone number from raw text (fallback method).

        This method searches the entire text for phone patterns, which can catch
        phone numbers that span multiple lines or have unusual formatting.

        Args:
            text: Full receipt text

        Returns:
            Restaurant phone number string or None
        """
        if not text:
            return None

        # Phone number patterns (same as line-based extraction)
        phone_patterns = [
            r"\(?\d{3}\)?\s*-?\s*\d{3}\s*-?\s*\d{4}",  # (XXX) XXX-XXXX or XXX-XXX-XXXX
            r"\d{3}\.\d{3}\.\d{4}",  # XXX.XXX.XXXX
            r"\d{3}\s+\d{3}\s+\d{4}",  # XXX XXX XXXX
            r"\d{3}-\d{3}-\d{4}",  # XXX-XXX-XXXX (explicit dashes)
            r"\(\d{3}\)\s*\d{3}-\d{4}",  # (XXX) XXX-XXXX
            r"\(\d{3}\)\s*\d{3}\.\d{4}",  # (XXX) XXX.XXXX
        ]

        # Try each phone pattern on the full text
        for pattern in phone_patterns:
            matches = list(re.finditer(pattern, text))
            for match in matches:
                phone = match.group(0).strip()
                # Extract all digits from the match
                digits_only = re.sub(r"\D", "", phone)

                # Skip if it's clearly not a phone number
                # - All same digits
                if len(set(digits_only)) <= 2:
                    continue

                # - Check if it's part of a date pattern
                context_start = max(0, match.start() - 10)
                context_end = min(len(text), match.end() + 10)
                context = text[context_start:context_end]
                if re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}", context):
                    continue

                # Validate: should have 10 digits (US phone number)
                if len(digits_only) == 10:
                    # Additional validation: area code shouldn't start with 0 or 1
                    if digits_only[0] in ["0", "1"]:
                        continue
                    # Format as (XXX) XXX-XXXX for consistency
                    formatted_phone = f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
                    current_app.logger.debug(f"Extracted restaurant phone from raw text: '{formatted_phone}'")
                    return formatted_phone
                elif len(digits_only) == 11 and digits_only[0] == "1":
                    # US number with country code - remove leading 1
                    digits_only = digits_only[1:]
                    if digits_only[0] in ["0", "1"]:
                        continue
                    formatted_phone = f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
                    current_app.logger.debug(
                        f"Extracted restaurant phone from raw text (with country code): '{formatted_phone}'"
                    )
                    return formatted_phone

        current_app.logger.debug("No restaurant phone found in raw text")
        return None

    def _extract_restaurant_website(self, lines: list[str]) -> str | None:
        """Extract restaurant website from receipt lines.

        Websites are typically found near the restaurant name and address,
        usually within the first 10-15 lines of a receipt.

        Args:
            lines: List of text lines from receipt

        Returns:
            Restaurant website URL string or None
        """
        if not lines:
            return None

        # Website patterns
        website_patterns = [
            r"https?://(?:www\.)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}",  # http:// or https://
            r"www\.([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}",  # www.example.com
            r"(?:^|[^a-zA-Z0-9])([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?:[^a-zA-Z0-9]|$)",  # example.com (standalone)
        ]

        # Skip words that indicate non-website lines
        skip_words = {
            "receipt",
            "invoice",
            "thank",
            "you",
            "visit",
            "us",
            "again",
            "outlook",
            "gmail",
            "yahoo",
            "hotmail",
            "from",
            "to",
            "date",
            "subject",
            "sent",
            "reply",
            "no-reply",
            "order",
            "check",
        }

        # Look for website in first 20 lines
        for idx, line in enumerate(lines[:20]):
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            # Skip empty lines
            if not line_stripped or len(line_stripped) < 4:
                continue

            # Skip lines with skip words
            if any(word in line_lower for word in skip_words):
                continue

            # Skip email addresses (contain @ but not www or http)
            if "@" in line_stripped and "www" not in line_lower and "http" not in line_lower:
                continue

            # Skip lines that are just amounts
            if re.match(r"^\$?\s*\d+\.\d{2}$", line_stripped):
                continue

            # Skip date patterns
            if re.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$", line_stripped):
                continue

            # Try each website pattern
            for pattern in website_patterns:
                match = re.search(pattern, line_stripped, re.IGNORECASE)
                if match:
                    website = match.group(0).strip()
                    # Clean up the website
                    # Remove leading/trailing punctuation
                    website = re.sub(r"^[^\w]+|[^\w]+$", "", website)
                    # Normalize: add https:// if no protocol
                    if not website.startswith(("http://", "https://")):
                        website = "https://" + website
                    # Ensure lowercase for consistency
                    website = website.lower()
                    current_app.logger.debug(
                        f"Extracted restaurant website: '{website}' from line {idx}: '{line_stripped}'"
                    )
                    return website

        current_app.logger.debug("No restaurant website found in first 20 lines")
        return None

    def _extract_date(self, text: str) -> datetime | None:
        """Extract date from receipt text.

        Args:
            text: Full receipt text

        Returns:
            Parsed datetime or None
        """
        # Common date patterns in receipts
        date_patterns = [
            r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",  # MM/DD/YYYY or DD/MM/YYYY
            r"\d{4}[/-]\d{1,2}[/-]\d{1,2}",  # YYYY/MM/DD
            r"\d{1,2}\s+\w{3,9}\s+\d{2,4}",  # DD Month YYYY
            r"\w{3,9}\s+\d{1,2},?\s+\d{2,4}",  # Month DD, YYYY
        ]

        for pattern in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                date_str = match.group()
                try:
                    # Try parsing with common formats
                    for fmt in ["%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%m-%d-%Y", "%d-%m-%Y"]:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            # Assume current year if year is 2 digits
                            if parsed_date.year < 2000:
                                parsed_date = parsed_date.replace(year=datetime.now().year)
                            return parsed_date
                        except ValueError:
                            continue
                except (AttributeError, TypeError, IndexError):
                    # Skip invalid matches (e.g., regex group() failures, type mismatches)
                    continue

        return None

    def _extract_time(self, text: str, lines: list[str]) -> str | None:
        """Extract time from receipt text.

        Looks for time patterns like "12:55 PM", "14:30", etc.
        Typically found near the date on receipts.

        Args:
            text: Full receipt text
            lines: List of text lines from receipt

        Returns:
            Time string in HH:MM AM/PM format or None
        """
        # Common time patterns in receipts
        time_patterns = [
            r"\b(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)\b",  # "12:55 PM" or "9:30 AM"
            r"\b(\d{1,2}):(\d{2})\b",  # "12:55" or "9:30" (24-hour or 12-hour without AM/PM)
            r"\b(\d{2}):(\d{2}):(\d{2})\s*(AM|PM|am|pm)?\b",  # "12:55:30 PM" (with seconds)
        ]

        # First, try to find time near date (common pattern: "10/5/25 12:55 PM")
        date_time_patterns = [
            r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)\b",  # Date + time with AM/PM
            r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+(\d{1,2}):(\d{2})\b",  # Date + time without AM/PM
        ]

        for pattern in date_time_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    am_pm = match.group(3) if len(match.groups()) >= 3 and match.group(3) else None

                    # Validate hour and minute
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        # Format time string
                        if am_pm:
                            # Already has AM/PM
                            time_str = f"{hour}:{minute:02d} {am_pm.upper()}"
                        else:
                            # No AM/PM, assume 12-hour format if hour <= 12, otherwise 24-hour
                            if hour == 0:
                                time_str = f"12:{minute:02d} AM"
                            elif hour < 12:
                                time_str = f"{hour}:{minute:02d} AM"
                            elif hour == 12:
                                time_str = f"12:{minute:02d} PM"
                            else:
                                time_str = f"{hour - 12}:{minute:02d} PM"

                        current_app.logger.debug(f"Extracted time from date+time pattern: '{time_str}'")
                        return time_str
                except (ValueError, IndexError):
                    continue

        # If no date+time pattern found, look for standalone time patterns
        for pattern in time_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    am_pm = None
                    if len(match.groups()) >= 3:
                        am_pm = match.group(3)

                    # Validate hour and minute
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        # Format time string
                        if am_pm:
                            # Already has AM/PM
                            time_str = f"{hour}:{minute:02d} {am_pm.upper()}"
                        else:
                            # No AM/PM, assume 12-hour format if hour <= 12, otherwise 24-hour
                            if hour == 0:
                                time_str = f"12:{minute:02d} AM"
                            elif hour < 12:
                                time_str = f"{hour}:{minute:02d} AM"
                            elif hour == 12:
                                time_str = f"12:{minute:02d} PM"
                            else:
                                time_str = f"{hour - 12}:{minute:02d} PM"

                        current_app.logger.debug(f"Extracted time from standalone pattern: '{time_str}'")
                        return time_str
                except (ValueError, IndexError):
                    continue

        current_app.logger.debug("No time found in receipt text")
        return None

    def _extract_amounts(self, text: str, lines: list[str]) -> dict[str, Decimal | None]:
        """Extract monetary amounts from receipt using multiple strategies.

        Improved extraction that:
        1. Looks for labeled amounts (TOTAL, TAX, etc.)
        2. Finds all amounts and scores them
        3. Uses position and context clues
        4. Handles OCR errors better

        Args:
            text: Full receipt text
            lines: List of text lines

        Returns:
            Dictionary with 'total', 'tax', 'tip', 'subtotal' keys
        """
        amounts: dict[str, Decimal | None] = {
            "total": None,
            "tax": None,
            "tip": None,
            "subtotal": None,
        }

        # More flexible amount patterns to handle OCR errors
        # Common OCR mistakes: O instead of 0, S instead of 5, I instead of 1
        amount_patterns = [
            r"\$?\s*(\d{1,3}(?:[,\s]\d{3})*(?:[.,]\d{2})?)",  # Standard: $25.50, 25.50
            r"\$?\s*(\d+[.,]\d{2})",  # Simple: 25.50 or 25,50
            r"(\d{1,3}(?:[,\s]\d{3})*[.,]\d{2})",  # Without $: 25.50
            r"(\d+[.,]\d{1,2})",  # Allow 1 or 2 decimal places
        ]

        # Look for labeled amounts (TOTAL, TAX, TIP, SUBTOTAL)
        labels = {
            "total": ["total", "amount due", "grand total", "final total", "balance", "amount", "charge"],
            "tax": ["tax", "sales tax", "gst", "vat", "hst", "taxes"],
            "tip": ["tip", "gratuity", "service"],
            "subtotal": ["subtotal", "sub-total", "total before tax", "sub total"],
        }

        text_lower = text.lower()

        # Strategy 1: Find labeled amounts (prioritize these - they're most accurate)
        # Check both same-line and next-line patterns (some receipts put label and amount on separate lines)
        for amount_type, keywords in labels.items():
            # Pattern 1: keyword and amount on same line
            for keyword in keywords:
                for pattern in amount_patterns:
                    search_patterns = [
                        rf"{keyword}\s*[:=]?\s*{pattern}",  # "Total: $17.06" or "Total $17.06"
                        rf"{pattern}\s+{keyword}",  # "$17.06 Total"
                    ]
                    for search_pattern in search_patterns:
                        matches = re.finditer(search_pattern, text_lower, re.IGNORECASE)
                        for match in matches:
                            try:
                                amount_str = match.group(1).replace(",", "").replace(" ", "").replace(",", ".")
                                # Handle European decimal format (comma instead of period)
                                if "," in amount_str and "." not in amount_str:
                                    amount_str = amount_str.replace(",", ".")
                                amount = Decimal(amount_str)

                                # Filter out phone numbers (3-digit numbers without decimals)
                                if amount >= 100 and amount < 1000 and "." not in match.group(0):
                                    continue

                                # Filter reasonable amounts
                                if 0.01 <= amount <= 10000:
                                    current_amount = amounts[amount_type]
                                    if current_amount is None or amount > current_amount:
                                        amounts[amount_type] = amount
                                        current_app.logger.debug(
                                            f"Found labeled {amount_type}: ${amount} (same-line pattern: {search_pattern})"
                                        )
                            except (InvalidOperation, ValueError):
                                continue

            # Pattern 2: keyword on one line, amount on next line (common receipt format)
            # Check all lines for keyword-only lines, then check next line for amounts
            # IMPORTANT: Pattern 2 always overrides Pattern 1 when it finds a labeled amount
            # because next-line matching is more accurate than same-line pattern matching
            # Force Pattern 2 to run by resetting the amount if Pattern 1 found something suspicious
            # (like a 3-digit number without decimals, which is likely a phone number)
            current_amount = amounts[amount_type]
            if current_amount is not None:
                # Check if Pattern 1 found a suspicious value (3-digit number without decimals)
                if 100 <= current_amount < 1000:
                    # Likely a phone number, reset to None so Pattern 2 can find the real amount
                    amounts[amount_type] = None

            for keyword in keywords:
                keyword_pattern = rf"^\s*{keyword}\s*$"
                for idx, line in enumerate(lines):
                    line_stripped = line.strip()
                    line_lower = line_stripped.lower()
                    # Match lines that are just the keyword (e.g., "Total", "Tax", "Subtotal")
                    if re.match(keyword_pattern, line_lower, re.IGNORECASE):
                        current_app.logger.debug(f"Found keyword '{keyword}' on line {idx}: '{line_stripped}'")
                        # Found keyword-only line, check next line for amount
                        if idx + 1 < len(lines):
                            next_line = lines[idx + 1]
                            current_app.logger.debug(f"  Checking next line {idx+1} for amount: '{next_line.strip()}'")
                            # Try all amount patterns on the next line
                            for pattern_idx, pattern_check in enumerate(amount_patterns):
                                amount_match = re.search(pattern_check, next_line)
                                if amount_match:
                                    current_app.logger.debug(
                                        f"    Pattern {pattern_idx} matched: {amount_match.group(0)}"
                                    )
                                    try:
                                        amount_str = (
                                            amount_match.group(1).replace(",", "").replace(" ", "").replace(",", ".")
                                        )
                                        if "," in amount_str and "." not in amount_str:
                                            amount_str = amount_str.replace(",", ".")
                                        amount = Decimal(amount_str)
                                        current_app.logger.debug(f"    Parsed amount: {amount}")

                                        # Filter out phone numbers
                                        if amount >= 100 and amount < 1000 and "." not in amount_match.group(0):
                                            current_app.logger.debug("    Skipped (phone number filter)")
                                            continue

                                        # Filter reasonable amounts
                                        if 0.01 <= amount <= 10000:
                                            # Pattern 2 (next-line matching) is more accurate than Pattern 1,
                                            # so always override Pattern 1's value when we find a labeled amount
                                            amounts[amount_type] = amount
                                            current_app.logger.debug(
                                                f"Found labeled {amount_type}: ${amount} "
                                                f"(keyword '{keyword}' on line {idx}='{line_stripped}', "
                                                f"amount on line {idx+1}='{next_line.strip()}')"
                                            )
                                            break  # Found amount for this keyword, move to next keyword
                                        else:
                                            current_app.logger.debug("    Skipped (outside range)")
                                    except (InvalidOperation, ValueError) as e:
                                        current_app.logger.debug(f"    Error parsing amount: {e}")
                                        continue
                            # If we found an amount for this keyword, don't check more lines for this keyword
                            # (but continue checking other keywords for this amount_type)
                            if amounts[amount_type] is not None:
                                break  # Break from line loop, continue to next keyword

        # Strategy 2: Extract ALL amounts and score them
        all_amounts: list[tuple[Decimal, int, str]] = []  # (amount, line_index, line_text)

        # Phone number patterns to exclude (common false positives)
        phone_patterns = [
            r"\(\d{3}\)\s*\d{3}[-.]?\d{4}",  # (972) 437-8440
            r"\d{3}[-.]?\d{3}[-.]?\d{4}",  # 972-437-8440
            r"\d{10}",  # 9724378440
        ]

        current_app.logger.debug(f"Scanning {len(lines)} lines for amounts using {len(amount_patterns)} patterns")
        for idx, line in enumerate(lines):
            # Skip lines that are clearly phone numbers
            if any(re.search(pattern, line) for pattern in phone_patterns):
                current_app.logger.debug(f"  Line {idx}: Skipping line with phone number pattern: '{line[:80]}'")
                continue

            for pattern_idx, pattern in enumerate(amount_patterns):
                matches_list = list(re.finditer(pattern, line))
                if matches_list:
                    current_app.logger.debug(
                        f"  Line {idx} (pattern {pattern_idx}): Found {len(matches_list)} matches in '{line[:80]}'"
                    )
                for match in matches_list:
                    try:
                        amount_str = match.group(1).replace(",", "").replace(" ", "").replace(",", ".")
                        if "," in amount_str and "." not in amount_str:
                            amount_str = amount_str.replace(",", ".")
                        amount = Decimal(amount_str)

                        # Filter out phone numbers (3-digit numbers without decimals are often phone area codes)
                        # But allow small amounts like $0.50
                        if amount >= 100 and amount < 1000 and "." not in match.group(0):
                            # Check if this looks like part of a phone number
                            line_context = line[max(0, match.start() - 10) : min(len(line), match.end() + 10)]
                            # Skip if near phone number indicators: parentheses, dashes, or other digits
                            if (
                                re.search(r"[()\-\.]", line_context)
                                or re.search(r"\d{3,}", line_context)
                                or re.search(r"phone|tel|call", line_context, re.IGNORECASE)
                            ):
                                current_app.logger.debug(
                                    f"    -> Skipped ${amount} (likely phone number part) from '{line[:60]}'"
                                )
                                continue
                            # Also skip standalone 3-digit numbers (very likely phone area codes)
                            # unless they're clearly part of a price (have $ sign or are near price keywords)
                            if not re.search(r"\$|price|cost|amount|total|tax|tip", line_context, re.IGNORECASE):
                                current_app.logger.debug(
                                    f"    -> Skipped ${amount} (standalone 3-digit number, likely phone) from '{line[:60]}'"
                                )
                                continue

                        # Filter reasonable amounts (0.01 to 10000)
                        if 0.01 <= amount <= 10000:
                            all_amounts.append((amount, idx, line.lower()))
                            current_app.logger.debug(f"    -> Extracted amount: ${amount} from '{match.group(0)}'")
                        else:
                            current_app.logger.debug(f"    -> Skipped amount ${amount} (outside reasonable range)")
                    except (InvalidOperation, ValueError) as e:
                        current_app.logger.debug(f"    -> Failed to parse amount from '{match.group(0)}': {e}")
                        continue

        # Strategy 3: If total not found, use heuristics
        if amounts["total"] is None:
            # Look at last 10 lines (totals are usually at the end)
            # Filter out phone numbers (3-digit numbers without decimals)
            end_amounts = [
                amt
                for amt, idx, line_text in all_amounts
                if idx >= len(lines) - 10 and not (100 <= amt < 1000 and "." not in str(amt))
            ]
            if end_amounts:
                # Prefer larger amounts at the end (likely the total)
                amounts["total"] = max(end_amounts)
            else:
                # Fallback: largest amount overall (excluding phone numbers)
                valid_amounts = [amt for amt, _, _ in all_amounts if not (100 <= amt < 1000 and "." not in str(amt))]
                if valid_amounts:
                    amounts["total"] = max(valid_amounts)

        # Strategy 4: If subtotal not found but we have total and tax, calculate it
        if amounts["subtotal"] is None and amounts["total"] and amounts["tax"]:
            try:
                calculated_subtotal = amounts["total"] - amounts["tax"]
                if amounts["tip"]:
                    calculated_subtotal = calculated_subtotal - amounts["tip"]
                if calculated_subtotal > 0:
                    amounts["subtotal"] = calculated_subtotal
            except (TypeError, InvalidOperation, AttributeError):
                # Skip if types are incompatible or arithmetic fails
                pass

        # Strategy 5: Look for amounts near common keywords even without explicit labels
        if amounts["total"] is None and all_amounts:
            # Score amounts based on context
            scored_amounts: list[tuple[Decimal, float]] = []
            for amount, idx, line_text in all_amounts:
                # Skip phone numbers (3-digit numbers without decimals)
                if 100 <= amount < 1000 and "." not in str(amount):
                    continue

                score = 0.0
                # Higher score for amounts at end of receipt
                if idx >= len(lines) - 5:
                    score += 10.0
                elif idx >= len(lines) - 10:
                    score += 5.0
                # Higher score if line contains total-related keywords
                if any(word in line_text for word in ["total", "amount", "due", "balance", "charge", "pay"]):
                    score += 15.0
                # Higher score for larger amounts (likely totals)
                if amount >= 10:
                    score += 5.0
                scored_amounts.append((amount, score))

            if scored_amounts:
                # Get amount with highest score
                amounts["total"] = max(scored_amounts, key=lambda x: x[1])[0]

        # Log ALL extracted amounts for debugging
        current_app.logger.debug("=" * 60)
        current_app.logger.debug("AMOUNT EXTRACTION DEBUG")
        current_app.logger.debug("=" * 60)
        current_app.logger.debug(f"Found {len(all_amounts)} total amounts in receipt:")
        for amount, idx, line_text in all_amounts[:20]:  # Show first 20
            current_app.logger.debug(f"  Line {idx}: ${amount} - '{line_text[:60]}'")
        if len(all_amounts) > 20:
            current_app.logger.debug(f"  ... and {len(all_amounts) - 20} more amounts")

        current_app.logger.debug("\nExtracted labeled amounts:")
        current_app.logger.debug(f"  Total: {amounts['total']}")
        current_app.logger.debug(f"  Tax: {amounts['tax']}")
        current_app.logger.debug(f"  Tip: {amounts['tip']}")
        current_app.logger.debug(f"  Subtotal: {amounts['subtotal']}")
        current_app.logger.debug("=" * 60)

        return amounts

    def _find_largest_amount(self, lines: list[str]) -> Decimal | None:
        """Find the largest monetary amount in given lines (likely the total).

        Uses multiple patterns to handle OCR errors better.

        Args:
            lines: List of text lines

        Returns:
            Largest amount found or None
        """
        amount_patterns = [
            r"\$?\s*(\d{1,3}(?:[,\s]\d{3})*(?:[.,]\d{2})?)",
            r"\$?\s*(\d+[.,]\d{2})",
            r"(\d{1,3}(?:[,\s]\d{3})*[.,]\d{2})",
            r"(\d+[.,]\d{1,2})",
        ]
        amounts_found: list[Decimal] = []

        for line in lines:
            for pattern in amount_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    try:
                        amount_str = match.group(1).replace(",", "").replace(" ", "").replace(",", ".")
                        if "," in amount_str and "." not in amount_str:
                            amount_str = amount_str.replace(",", ".")
                        amount = Decimal(amount_str)
                        # Filter out unrealistic amounts (likely errors)
                        if 0.01 <= amount <= 10000:  # Reasonable range for meal expenses
                            amounts_found.append(amount)
                    except (InvalidOperation, ValueError):
                        continue

        return max(amounts_found) if amounts_found else None

    def _extract_items(self, lines: list[str]) -> list[str]:
        """Extract line items from receipt.

        Args:
            lines: List of text lines

        Returns:
            List of item names
        """
        items: list[str] = []
        skip_patterns = [
            r"^total",
            r"^tax",
            r"^tip",
            r"^subtotal",
            r"^\$?\s*\d+\.\d{2}$",  # Just an amount
            r"^\d+[/-]\d+[/-]\d+",  # Date
            r"^from\s+|^to\s+|^subject\s+|^date\s+",  # Email headers
            r".*@.*",  # Email addresses
            r"^server\s*:|^check\s*#|^ordered\s*:",  # Receipt metadata
            r"^thank\s+you",  # Footer text
        ]

        # Skip words that indicate non-item lines
        skip_words = {
            "receipt",
            "invoice",
            "thank",
            "you",
            "visit",
            "us",
            "again",
            "server",
            "check",
            "ordered",
            "from",
            "to",
            "date",
            "subject",
            "outlook",
            "gmail",
            "yahoo",
            "hotmail",
            "no-reply",
        }

        # Items are usually in the middle section, between header and totals
        # Skip first 3-5 lines (header/email) and last 5-7 lines (totals/footer)
        start_idx = min(5, len(lines))
        end_idx = max(len(lines) - 7, start_idx)

        current_app.logger.debug(
            f"Extracting items from lines {start_idx} to {end_idx} (out of {len(lines)} total lines)"
        )

        for line in lines[start_idx:end_idx]:
            line_clean = line.strip()
            if not line_clean:
                continue

            line_lower = line_clean.lower()

            # Skip if matches skip patterns
            if any(re.match(pattern, line_clean, re.IGNORECASE) for pattern in skip_patterns):
                current_app.logger.debug(f"Skipping item line (matches skip pattern): '{line_clean[:60]}'")
                continue

            # Skip if contains skip words
            if any(word in line_lower for word in skip_words):
                current_app.logger.debug(f"Skipping item line (contains skip word): '{line_clean[:60]}'")
                continue

            # Skip time patterns
            if re.match(r"^\d{1,2}:\d{2}\s*(AM|PM|am|pm)?$", line_clean, re.IGNORECASE):
                continue

            # Extract item name (remove trailing amount if present)
            # Pattern: item name followed by optional price
            item_match = re.match(r"^(.+?)\s+\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*$", line_clean)
            if item_match:
                item_name = item_match.group(1).strip()
                price = item_match.group(2)
                # Verify it's a reasonable price (not a phone number or date)
                try:
                    price_val = Decimal(price.replace(",", ""))
                    if price_val > 1000:  # Likely not a price
                        continue
                except (InvalidOperation, ValueError):
                    pass
            else:
                # Try pattern without dollar sign
                item_match = re.match(r"^(.+?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*$", line_clean)
                if item_match:
                    item_name = item_match.group(1).strip()
                else:
                    # No price found, use whole line if it looks like an item
                    item_name = line_clean

            # Clean up item name
            item_name = re.sub(r"^\d+\s*", "", item_name)  # Remove leading numbers
            item_name = re.sub(r"\s+", " ", item_name).strip()  # Normalize whitespace

            # Must have at least 3 characters and some letters
            if len(item_name) >= 3 and re.search(r"[a-zA-Z]{2,}", item_name):
                if item_name.lower() not in ["item", "description", "qty", "quantity", "price"]:
                    items.append(item_name)
                    current_app.logger.debug(f"Extracted item: '{item_name}' from line '{line_clean[:60]}'")

        current_app.logger.debug(f"Extracted {len(items)} items total")
        return items[:10]  # Limit to 10 items

    def _is_bank_statement(self, text: str, lines: list[str]) -> bool:
        """Detect if the document is a bank statement.

        Args:
            text: Full text content
            lines: List of text lines

        Returns:
            True if document appears to be a bank statement
        """
        text_lower = text.lower()

        # Strong bank statement indicators (more specific)
        strong_indicators = [
            "account statement",
            "bank statement",
            "checking account",
            "savings account",
            "account number",
            "statement period",
            "available balance",
            "pending transaction",
            "routing number",
        ]

        # Weak indicators (can appear in receipts too)
        weak_indicators = [
            "transaction",
            "balance",
            "debit",
            "credit",
        ]

        # Receipt indicators (if present, likely NOT a bank statement)
        receipt_indicators = [
            "receipt",
            "thank you",
            "subtotal",
            "tax",
            "tip",
            "total",
            "restaurant",
            "cafe",
            "grill",
            "diner",
        ]

        # Count strong indicators
        strong_count = sum(1 for indicator in strong_indicators if indicator in text_lower)

        # Count weak indicators
        weak_count = sum(1 for indicator in weak_indicators if indicator in text_lower)

        # Count receipt indicators
        receipt_count = sum(1 for indicator in receipt_indicators if indicator in text_lower)

        # Also check for tabular structure (common in bank statements)
        # Bank statements often have columns: Date | Description | Amount
        has_tabular_structure = False
        for line in lines[:20]:  # Check first 20 lines
            # Look for lines with multiple amounts or date patterns separated by spaces/tabs
            if re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}.*\$\d+", line):
                has_tabular_structure = True
                break

        # If we have strong receipt indicators, it's likely a receipt, not a bank statement
        if receipt_count >= 2:
            return False

        # Consider it a bank statement if:
        # - 2+ strong indicators, OR
        # - 1 strong indicator + tabular structure, OR
        # - 3+ weak indicators + tabular structure
        return (
            (strong_count >= 2)
            or (strong_count >= 1 and has_tabular_structure)
            or (weak_count >= 3 and has_tabular_structure)
        )

    def _parse_bank_statement(
        self,
        text: str,
        lines: list[str],
        form_hints: dict[str, Any] | None = None,
    ) -> ReceiptData:
        """Parse bank statement data to extract transaction information.

        Args:
            text: Full text content
            lines: List of text lines
            form_hints: Optional dictionary with form values to use as hints for matching

        Returns:
            ReceiptData object with parsed fields
        """
        receipt_data = ReceiptData(raw_text=text)

        # Extract transactions (date, merchant, amount pairs)
        transactions = self._extract_transactions(lines)

        # Log all extracted transactions for debugging
        current_app.logger.debug("=" * 60)
        current_app.logger.debug("BANK STATEMENT TRANSACTION EXTRACTION DEBUG")
        current_app.logger.debug("=" * 60)
        current_app.logger.debug(f"Found {len(transactions)} transactions:")
        for i, trans in enumerate(transactions[:10], 1):  # Show first 10
            current_app.logger.debug(f"  Transaction {i}:")
            current_app.logger.debug(f"    Date: {trans.get('date')}")
            current_app.logger.debug(f"    Merchant: {trans.get('merchant')}")
            current_app.logger.debug(f"    Amount: ${trans.get('amount')}")
            raw_line_value = trans.get("raw_line")
            if raw_line_value and isinstance(raw_line_value, str):
                current_app.logger.debug(f"    Raw line: {raw_line_value[:80]}")
        if len(transactions) > 10:
            current_app.logger.debug(f"  ... and {len(transactions) - 10} more transactions")
        current_app.logger.debug("=" * 60)

        # Find the best transaction using form hints if available
        best_transaction = self._find_best_transaction(transactions, form_hints=form_hints)

        if best_transaction:
            current_app.logger.debug(
                f"Selected best transaction: {best_transaction.get('merchant')} - ${best_transaction.get('amount')} on {best_transaction.get('date')}"
            )
        else:
            current_app.logger.debug("No best transaction found, using fallback extraction")

        if best_transaction:
            receipt_data.date = best_transaction.get("date")
            receipt_data.amount = best_transaction.get("amount")
            receipt_data.total = receipt_data.amount
            receipt_data.restaurant_name = best_transaction.get("merchant")
        else:
            # Fallback to individual extraction methods
            receipt_data.date = self._extract_transaction_date(text, lines)
            receipt_data.amount = self._extract_transaction_amount(text, lines)
            receipt_data.total = receipt_data.amount
            receipt_data.restaurant_name = self._extract_merchant_name(text, lines)

        # Calculate confidence scores
        receipt_data.confidence_scores = self._calculate_confidence_scores(receipt_data)

        return receipt_data

    def _extract_transaction_date(self, text: str, lines: list[str]) -> datetime | None:
        """Extract transaction date from bank statement.

        Bank statements typically show dates in MM/DD or MM/DD/YYYY format.
        We want the most recent transaction date.

        Args:
            text: Full text content
            lines: List of text lines

        Returns:
            Parsed datetime or None
        """
        # Look for date patterns, prioritizing those near amounts
        date_patterns = [
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",  # MM/DD/YYYY or MM/DD/YY
            r"(\d{1,2}[/-]\d{1,2})",  # MM/DD (current year assumed)
        ]

        dates_found: list[datetime] = []

        for line in lines:
            for pattern in date_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    date_str = match.group(1)
                    try:
                        # Try parsing with common formats
                        for fmt in ["%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y", "%m/%d/%y", "%d/%m/%y"]:
                            try:
                                parsed_date = datetime.strptime(date_str, fmt)
                                # If year is missing, assume current year
                                if parsed_date.year < 2000:
                                    parsed_date = parsed_date.replace(year=datetime.now().year)
                                dates_found.append(parsed_date)
                                break
                            except ValueError:
                                continue
                    except (AttributeError, TypeError, IndexError):
                        # Skip invalid matches (e.g., regex group() failures, type mismatches)
                        continue

        # Return the most recent date (likely the transaction date)
        if dates_found:
            return max(dates_found)

        # Fallback to standard date extraction
        return self._extract_date(text)

    def _extract_transaction_amount(self, text: str, lines: list[str]) -> Decimal | None:
        """Extract transaction amount from bank statement.

        Bank statements show amounts that may be negative (debits) or positive (credits).
        We want the absolute value of the transaction amount.

        Args:
            text: Full text content
            lines: List of text lines

        Returns:
            Transaction amount as Decimal or None
        """
        # Pattern for amounts: may include negative sign, parentheses, or just positive
        # Examples: -$25.50, ($25.50), $25.50, 25.50
        amount_patterns = [
            r"[-\(]?\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\)?",  # Standard amount
            r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*[DB]",  # Amount with Debit/Credit indicator
        ]

        amounts_found: list[Decimal] = []

        for line in lines:
            # Skip header lines
            if any(word in line.lower() for word in ["date", "description", "amount", "balance", "transaction"]):
                continue

            for pattern in amount_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    try:
                        amount_str = match.group(1).replace(",", "")
                        amount = Decimal(amount_str)
                        # Filter reasonable transaction amounts
                        if 0.01 <= amount <= 10000:
                            amounts_found.append(amount)
                    except (InvalidOperation, ValueError):
                        continue

        # For bank statements, we typically want the largest transaction amount
        # (which is likely the meal expense)
        if amounts_found:
            return max(amounts_found)

        return None

    def _extract_merchant_name(self, text: str, lines: list[str]) -> str | None:
        """Extract merchant/restaurant name from bank statement transaction description.

        Bank statements show merchant names in transaction descriptions.
        These are usually on lines that contain dates and amounts.

        Args:
            text: Full text content
            lines: List of text lines

        Returns:
            Merchant name or None
        """
        # Look for lines that contain both a date pattern and an amount
        # The merchant name is usually between them or after the date
        date_amount_pattern = r"\d{1,2}[/-]\d{1,2}[/-]?\d{0,4}"

        for line in lines:
            # Skip header lines
            if any(word in line.lower() for word in ["date", "description", "amount", "balance", "transaction"]):
                continue

            # Check if line has date and amount (likely a transaction line)
            if re.search(date_amount_pattern, line) and re.search(r"\$?\d+\.\d{2}", line):
                # Extract merchant name (text between date and amount, or after date)
                # Remove date and amount, clean up
                cleaned = re.sub(r"\d{1,2}[/-]\d{1,2}[/-]?\d{0,4}", "", line)
                cleaned = re.sub(r"\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?", "", cleaned)

                # Remove time patterns (12:55 PM, 12:55, etc.)
                cleaned = re.sub(r"\d{1,2}:\d{2}\s*(AM|PM|am|pm)?\s*", "", cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r"\s+", " ", cleaned).strip()

                # Remove common bank statement artifacts
                cleaned = re.sub(r"^(PUR|DEBIT|CREDIT|ACH|POS|CHECK)\s*", "", cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r"\s*\d{4,}.*$", "", cleaned)  # Remove account numbers at end

                # Skip if result is just a time pattern or has no letters
                time_pattern = re.match(r"^\d{1,2}:\d{2}\s*(AM|PM|am|pm)?$", cleaned, re.IGNORECASE)
                if time_pattern:
                    current_app.logger.debug(f"Skipping merchant extraction - '{cleaned}' is a time pattern")
                    continue

                if not re.search(r"[a-zA-Z]{2,}", cleaned):
                    current_app.logger.debug(f"Skipping merchant extraction - '{cleaned}' has no letters")
                    continue

                if len(cleaned) > 2 and len(cleaned) < 100:
                    # Clean up common suffixes
                    cleaned = re.sub(
                        r"\s+(INC|LLC|CORP|RESTAURANT|REST|CAFE|GRILL).*$", "", cleaned, flags=re.IGNORECASE
                    )
                    return cleaned.strip()

        # Fallback: look for restaurant-like names in the text
        name_result = self._extract_restaurant_name(lines)
        # Extract just the name (first element of tuple), ignore location number
        return name_result[0] if name_result else None

    def _extract_transactions(self, lines: list[str]) -> list[dict[str, Any]]:
        """Extract transaction data from bank statement lines.

        Improved extraction that handles various bank statement formats:
        - Tabular formats (Date | Description | Amount)
        - Multi-line transactions
        - Various date and amount formats

        Args:
            lines: List of text lines from bank statement

        Returns:
            List of transaction dictionaries with 'date', 'merchant', 'amount' keys
        """
        transactions: list[dict[str, Any]] = []
        # More flexible date patterns
        date_patterns = [
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",  # MM/DD/YYYY or DD/MM/YYYY
            r"(\d{1,2}[/-]\d{1,2})",  # MM/DD (current year assumed)
            r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})",  # YYYY/MM/DD
        ]
        # More flexible amount patterns (handles negatives, parentheses, etc.)
        amount_patterns = [
            r"[-\(]?\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\)?",  # Standard: -$25.50, ($25.50), $25.50
            r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*[DB]",  # With Debit/Credit indicator
            r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*CR",  # Credit indicator
            r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*DR",  # Debit indicator
        ]

        # Track if we're in a transaction section (skip headers)
        in_transaction_section = False
        header_keywords = ["date", "description", "amount", "balance", "transaction", "account", "statement"]

        for i, line in enumerate(lines):
            line_lower = line.lower().strip()

            # Detect start of transaction section
            if not in_transaction_section:
                # Look for header row that indicates transactions start
                if any(keyword in line_lower for keyword in header_keywords):
                    # Check if next few lines have transaction-like patterns
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        if re.search(r"\d{1,2}[/-]\d{1,2}", next_line) and re.search(r"\$?\d+\.\d{2}", next_line):
                            in_transaction_section = True
                    continue
                # Also check if this line itself looks like a transaction
                if re.search(r"\d{1,2}[/-]\d{1,2}", line) and re.search(r"\$?\d+\.\d{2}", line):
                    in_transaction_section = True

            # Skip header lines even in transaction section
            if any(keyword in line_lower for keyword in header_keywords) and len(line_lower) < 50:
                continue

            # Try to find date and amount in this line
            date_match = None
            for pattern in date_patterns:
                date_match = re.search(pattern, line)
                if date_match:
                    break

            amount_match = None
            amount_value = None
            for pattern in amount_patterns:
                amount_match = re.search(pattern, line)
                if amount_match:
                    try:
                        amount_str = amount_match.group(1).replace(",", "")
                        amount_value = Decimal(amount_str)
                        break
                    except (InvalidOperation, ValueError):
                        continue

            # If we found both date and amount, extract transaction
            if date_match and amount_match and amount_value:
                try:
                    # Extract and parse date
                    date_str = date_match.group(1)
                    parsed_date = None
                    date_formats = [
                        "%m/%d/%Y",
                        "%d/%m/%Y",
                        "%Y/%m/%d",
                        "%m-%d-%Y",
                        "%d-%m-%Y",
                        "%Y-%m-%d",
                        "%m/%d/%y",
                        "%d/%m/%y",
                        "%m/%d",
                        "%d/%m",
                    ]

                    for fmt in date_formats:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            if parsed_date.year < 2000:
                                parsed_date = parsed_date.replace(year=datetime.now().year)
                            break
                        except ValueError:
                            continue

                    if not parsed_date:
                        continue

                    # Extract merchant name (text between date and amount, or after date)
                    date_start = date_match.start()
                    amount_start = amount_match.start()

                    # Get merchant text
                    if amount_start > date_start:
                        merchant = line[date_start + len(date_match.group()) : amount_start].strip()
                    else:
                        # Amount before date - get text after date
                        merchant = line[date_start + len(date_match.group()) :].strip()
                        # Remove amount if it appears after
                        merchant = re.sub(r"\s*[-\(]?\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?\)?\s*$", "", merchant)

                    # Clean up merchant name
                    merchant = re.sub(
                        r"^(PUR|DEBIT|CREDIT|ACH|POS|CHECK|CHK|ATM|TFR|XFER)\s*", "", merchant, flags=re.IGNORECASE
                    )
                    merchant = re.sub(r"\s*\d{4,}.*$", "", merchant)  # Remove account/transaction numbers at end
                    merchant = re.sub(r"^\d+\s+", "", merchant)  # Remove leading numbers

                    # Remove time patterns (12:55 PM, 12:55, etc.)
                    merchant = re.sub(r"\d{1,2}:\d{2}\s*(AM|PM|am|pm)?\s*", "", merchant, flags=re.IGNORECASE)
                    merchant = re.sub(r"\s+", " ", merchant).strip()  # Normalize whitespace

                    # Skip if merchant is just a time pattern or other invalid patterns
                    time_pattern = re.match(r"^\d{1,2}:\d{2}\s*(AM|PM|am|pm)?$", merchant, re.IGNORECASE)
                    if time_pattern:
                        current_app.logger.debug(f"Skipping transaction - merchant '{merchant}' is a time pattern")
                        continue

                    # Must have at least some letters (merchant names have letters)
                    if not re.search(r"[a-zA-Z]{2,}", merchant):
                        current_app.logger.debug(f"Skipping transaction - merchant '{merchant}' has no letters")
                        continue

                    # Filter reasonable transactions
                    if parsed_date and 0.01 <= amount_value <= 10000 and len(merchant) > 2 and len(merchant) < 150:
                        transactions.append(
                            {
                                "date": parsed_date,
                                "merchant": merchant,
                                "amount": abs(amount_value),  # Use absolute value
                                "raw_line": line,  # Keep original for debugging
                            }
                        )
                except (ValueError, InvalidOperation, Exception) as e:
                    current_app.logger.debug(f"Failed to parse transaction line: {line[:100]} - {e}")
                    continue

        # Log extracted transactions for debugging
        current_app.logger.debug(f"Extracted {len(transactions)} transactions from bank statement")
        if transactions:
            current_app.logger.debug(f"Sample transactions: {transactions[:3]}")

        return transactions

    def _find_best_transaction(
        self,
        transactions: list[dict[str, Any]],
        form_hints: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Find the best transaction from a list, using form hints if available.

        Args:
            transactions: List of transaction dictionaries
            form_hints: Optional dictionary with form values to use as hints:
                - amount: Expected amount (Decimal or str)
                - date: Expected date (datetime or str)
                - restaurant_name: Expected restaurant name (str)

        Returns:
            Best transaction dictionary or None
        """
        if not transactions:
            return None

        # Parse form hints
        expected_amount = None
        expected_date = None
        expected_restaurant = None

        if form_hints:
            # Parse expected amount
            if form_hints.get("amount"):
                try:
                    expected_amount = Decimal(str(form_hints["amount"]))
                except (InvalidOperation, ValueError):
                    pass

            # Parse expected date
            if form_hints.get("date"):
                date_val = form_hints["date"]
                if isinstance(date_val, str):
                    try:
                        expected_date = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
                    except ValueError:
                        try:
                            expected_date = datetime.strptime(date_val, "%Y-%m-%d")
                        except ValueError:
                            pass
                elif isinstance(date_val, datetime):
                    expected_date = date_val

            # Parse expected restaurant name
            if form_hints.get("restaurant_name"):
                expected_restaurant = str(form_hints["restaurant_name"]).strip().lower()

        # Restaurant-related keywords
        restaurant_keywords = [
            "restaurant",
            "cafe",
            "café",
            "diner",
            "grill",
            "bistro",
            "pizza",
            "sushi",
            "burger",
            "taco",
            "bar",
            "pub",
            "food",
            "kitchen",
            "dining",
            "eat",
            "chinese",
            "italian",
            "mexican",
            "japanese",
            "thai",
            "indian",
            "french",
        ]

        # Score transactions (higher score = better match)
        scored_transactions: list[tuple[dict[str, Any], float]] = []
        for trans in transactions:
            score = 0.0
            merchant_lower = trans.get("merchant", "").lower()
            trans_amount = trans.get("amount", Decimal(0))
            trans_date = trans.get("date")

            # HIGHEST PRIORITY: Match form hints if provided
            if expected_amount:
                amount_diff = abs(trans_amount - expected_amount)
                # Exact match or very close (±$0.10) gets highest score
                if amount_diff <= Decimal("0.10"):
                    score += 50.0  # Very high score for amount match
                elif amount_diff <= Decimal("1.00"):
                    score += 20.0  # Good score for close match
                elif amount_diff <= Decimal("5.00"):
                    score += 5.0  # Some score for reasonable match

            if expected_date and trans_date:
                date_diff = abs((trans_date.date() - expected_date.date()).days)
                if date_diff == 0:
                    score += 30.0  # Exact date match
                elif date_diff <= 1:
                    score += 20.0  # Close date match
                elif date_diff <= 7:
                    score += 5.0  # Within a week

            if expected_restaurant:
                import jellyfish

                similarity = jellyfish.jaro_winkler_similarity(expected_restaurant, merchant_lower)
                if similarity >= 0.9:
                    score += 40.0  # Very similar restaurant name
                elif similarity >= 0.7:
                    score += 20.0  # Similar restaurant name
                elif similarity >= 0.5:
                    score += 5.0  # Some similarity

            # SECONDARY: Restaurant keyword matching
            for keyword in restaurant_keywords:
                if keyword in merchant_lower:
                    score += 2.0

            # TERTIARY: Prefer recent transactions
            if trans_date:
                days_ago = (datetime.now() - trans_date).days
                if days_ago <= 30:
                    score += 1.0
                elif days_ago <= 90:
                    score += 0.5

            # TERTIARY: Prefer reasonable meal amounts ($5-$200)
            if 5 <= trans_amount <= 200:
                score += 1.0
            elif 200 < trans_amount <= 500:
                score += 0.5

            scored_transactions.append((trans, score))

        # Sort by score (highest first)
        scored_transactions.sort(key=lambda x: x[1], reverse=True)

        # Return best transaction if score > 0, otherwise return most recent
        if scored_transactions and scored_transactions[0][1] > 0:
            return scored_transactions[0][0]

        # Fallback: return most recent transaction
        if transactions:
            sorted_by_date = sorted(transactions, key=lambda x: x.get("date") or datetime.min, reverse=True)
            return sorted_by_date[0]

        return None

    def _calculate_confidence_scores(self, receipt_data: ReceiptData) -> dict[str, float]:
        """Calculate confidence scores for extracted fields.

        Args:
            receipt_data: ReceiptData object

        Returns:
            Dictionary of field names to confidence scores (0.0-1.0)
        """
        scores: dict[str, float] = {}

        # Simple confidence scoring based on successful extraction
        scores["amount"] = 0.9 if receipt_data.amount else 0.0
        scores["date"] = 0.8 if receipt_data.date else 0.0
        scores["restaurant_name"] = 0.85 if receipt_data.restaurant_name else 0.0
        scores["total"] = 0.9 if receipt_data.total else 0.0
        scores["items"] = min(0.7, len(receipt_data.items) * 0.1) if receipt_data.items else 0.0

        return scores


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
