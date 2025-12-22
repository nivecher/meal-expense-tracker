#!/usr/bin/env python3
"""Command-line script to extract receipt information from images or PDFs using OCR.

This script uses Tesseract OCR to extract structured data from receipt images or PDFs,
similar to the OCR service used in the web application.

Usage:
    python scripts/extract_receipt.py <file_path> [--output-format json|text] [--tesseract-cmd PATH]
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
import sys
from typing import Any, cast

from PIL import Image, ImageEnhance, ImageFilter
import pytesseract  # type: ignore[import-untyped]

try:
    import fitz  # type: ignore[import-untyped]  # PyMuPDF
except ImportError:
    fitz = None

# Keep pdf2image as fallback for systems without PyMuPDF
try:
    from pdf2image import convert_from_bytes  # type: ignore[import-not-found]
except ImportError:
    convert_from_bytes = None

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

    def to_dict(self) -> dict[str, Any]:
        """Convert ReceiptData to dictionary with serializable values."""
        result = asdict(self)
        # Convert Decimal to string for JSON serialization
        for key in ["amount", "tax", "tip", "total"]:
            if result[key] is not None:
                result[key] = str(result[key])
        # Convert datetime to ISO format string
        if result["date"] is not None:
            result["date"] = result["date"].isoformat()
        return result


class StandaloneOCRService:
    """Standalone OCR service for command-line use (no Flask dependency)."""

    def __init__(self, tesseract_cmd: str | None = None, confidence_threshold: float = 0.7) -> None:
        """Initialize OCR service with configuration.

        Args:
            tesseract_cmd: Optional path to Tesseract binary
            confidence_threshold: Minimum confidence threshold (not used in current implementation)
        """
        self.confidence_threshold = confidence_threshold
        self.tesseract_cmd = tesseract_cmd

        # Set Tesseract command path if provided
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

        # Verify Tesseract is available
        try:
            pytesseract.get_tesseract_version()
            logger.info("Tesseract OCR initialized successfully")
        except pytesseract.TesseractNotFoundError:
            logger.error(
                "Tesseract OCR binary not found. Please install it:\n"
                "  Linux: sudo apt-get install tesseract-ocr\n"
                "  macOS: brew install tesseract\n"
                "  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki"
            )
            raise RuntimeError("Tesseract OCR not found") from None
        except Exception as e:
            logger.error(f"Tesseract OCR not available: {e}")
            raise RuntimeError(f"Tesseract OCR initialization failed: {e}") from e

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

        # Check if file is a PDF
        is_pdf = file_path_obj.suffix.lower() == ".pdf" or file_bytes[:4] == b"%PDF"

        # Try to extract text directly from PDF first (faster, more accurate)
        raw_text = ""
        if is_pdf and fitz is not None:
            try:
                raw_text = self._extract_text_from_pdf(file_bytes)
                if raw_text and len(raw_text.strip()) > 50:  # If we got substantial text
                    logger.debug("Extracted text directly from PDF (no OCR needed)")
                else:
                    raw_text = ""  # Fall through to OCR
            except Exception as e:
                logger.debug(f"Direct PDF text extraction failed, falling back to OCR: {e}")
                raw_text = ""

        # If no text extracted directly, use OCR (for images or scanned PDFs)
        if not raw_text:
            # Preprocess image/PDF
            try:
                processed_image = self._preprocess_image(file_bytes, str(file_path_obj))
            except Exception as e:
                logger.error(f"Image preprocessing failed: {e}")
                raise RuntimeError(f"Failed to preprocess image: {e}") from e

            # Extract text using Tesseract OCR
            try:
                raw_text = self._extract_text_with_tesseract(processed_image)
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
                logger.debug(f"Chunk {i//chunk_size + 1} (chars {i}-{min(i+chunk_size, len(raw_text))}):")
                logger.debug(chunk)
            logger.debug(f"\nTotal characters extracted: {len(raw_text)}")
        else:
            logger.debug("No text extracted from OCR")
        logger.debug("=" * 60)

        # Parse receipt data from extracted text
        receipt_data = self._parse_receipt_data(raw_text)

        return receipt_data

    def _extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Extract text directly from PDF if it has a text layer.

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
            logger.debug(f"Extracted {len(result)} characters directly from PDF")
            return result
        except Exception as e:
            logger.warning(f"PDF text extraction failed: {e}")
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
            # Try PyMuPDF first (no system dependencies)
            if fitz is not None:
                try:
                    doc = fitz.open(stream=image_bytes, filetype="pdf")
                    if len(doc) > 0:
                        page = doc[0]
                        # Render page as image at 300 DPI
                        mat = fitz.Matrix(300 / 72, 300 / 72)  # 300 DPI
                        pix = page.get_pixmap(matrix=mat)
                        # Convert to PIL Image
                        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                        doc.close()
                        logger.debug(f"Converted PDF to image using PyMuPDF: {img.size}")
                    else:
                        raise ValueError("PDF has no pages")
                except Exception as e:
                    logger.warning(f"PyMuPDF PDF conversion failed, trying pdf2image: {e}")
                    doc.close() if "doc" in locals() else None
                    # Fall back to pdf2image
                    if convert_from_bytes is None:
                        raise RuntimeError(
                            "PDF processing requires PyMuPDF or pdf2image library. "
                            "Install with: pip install PyMuPDF (recommended) or pip install pdf2image"
                        )
                    images = convert_from_bytes(image_bytes, first_page=1, last_page=1, dpi=300)
                    if not images:
                        raise ValueError("PDF conversion produced no images")
                    img = cast(Image.Image, images[0])
                    logger.debug(f"Converted PDF to image using pdf2image: {img.size}")
            elif convert_from_bytes is not None:
                # Fallback to pdf2image if PyMuPDF not available
                try:
                    images = convert_from_bytes(image_bytes, first_page=1, last_page=1, dpi=300)
                    if not images:
                        raise ValueError("PDF conversion produced no images")
                    img = cast(Image.Image, images[0])
                    logger.debug(f"Converted PDF to image using pdf2image: {img.size}")
                except Exception as e:
                    logger.error(f"PDF conversion failed: {e}")
                    raise RuntimeError(f"Failed to convert PDF to image: {e}") from e
            else:
                raise RuntimeError(
                    "PDF processing requires PyMuPDF or pdf2image library. "
                    "Install with: pip install PyMuPDF (recommended, no system deps) or pip install pdf2image"
                )
        else:
            # Open image from bytes
            try:
                img = cast(Image.Image, Image.open(BytesIO(image_bytes)))
            except Exception as e:
                logger.error(f"Failed to open image: {e}")
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
            logger.debug(f"Resized image from {img.size} to {new_size}")

        # Convert to grayscale
        img = cast(Image.Image, img.convert("L"))

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = cast(Image.Image, enhancer.enhance(1.5))

        # Apply slight sharpening
        img = cast(Image.Image, img.filter(ImageFilter.SHARPEN))

        return cast(Image.Image, img)

    def _extract_text_with_tesseract(self, image: Image.Image) -> str:
        """Extract text from image using Tesseract OCR.

        Args:
            image: Preprocessed PIL Image

        Returns:
            Extracted text string
        """
        # Configure Tesseract for better receipt recognition
        custom_config = r"--oem 3 --psm 6"  # Assume uniform block of text

        try:
            text = cast(str, pytesseract.image_to_string(image, config=custom_config))
            logger.debug(f"Extracted {len(text)} characters from receipt")
            return text
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            raise RuntimeError(f"OCR processing failed: {e}") from e

    def _parse_receipt_data(self, raw_text: str) -> ReceiptData:
        """Parse receipt data from extracted text.

        Args:
            raw_text: Raw text extracted from OCR

        Returns:
            ReceiptData object with parsed fields
        """
        receipt_data = ReceiptData(raw_text=raw_text)
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

        # Log ALL lines for debugging
        logger.debug("=" * 60)
        logger.debug("ALL LINES FROM OCR TEXT:")
        logger.debug("=" * 60)
        logger.debug(f"Total lines found: {len(lines)}")
        for i, line in enumerate(lines, 1):
            logger.debug(f"  Line {i}: {line}")
        logger.debug("=" * 60)

        if not lines:
            logger.warning("No lines found in OCR text - returning empty ReceiptData")
            return receipt_data

        # Detect if this is a bank statement vs receipt
        is_bank_statement = self._is_bank_statement(raw_text, lines)

        if is_bank_statement:
            logger.debug("Detected bank statement format")
            return self._parse_bank_statement(raw_text, lines)

        # Standard receipt parsing
        # Extract restaurant name (usually first or second line)
        name_result = self._extract_restaurant_name(lines)
        receipt_data.restaurant_name, receipt_data.restaurant_location_number = name_result
        logger.debug(f"Extracted restaurant name: {receipt_data.restaurant_name}")
        if receipt_data.restaurant_location_number:
            logger.debug(f"Extracted restaurant location number: {receipt_data.restaurant_location_number}")

        # Extract restaurant address
        receipt_data.restaurant_address = self._extract_restaurant_address(lines)
        logger.debug(f"Extracted restaurant address: {receipt_data.restaurant_address}")

        # Extract restaurant phone (try lines first, then fallback to raw text)
        receipt_data.restaurant_phone = self._extract_restaurant_phone(lines)
        if not receipt_data.restaurant_phone:
            # Fallback: search raw text directly (handles phone numbers split across lines)
            receipt_data.restaurant_phone = self._extract_restaurant_phone_from_text(raw_text)
        logger.debug(f"Extracted restaurant phone: {receipt_data.restaurant_phone}")

        # Extract restaurant website
        receipt_data.restaurant_website = self._extract_restaurant_website(lines)
        logger.debug(f"Extracted restaurant website: {receipt_data.restaurant_website}")

        # Extract date and time
        receipt_data.date = self._extract_date(raw_text)
        receipt_data.time = self._extract_time(raw_text, lines)
        logger.debug(f"Extracted date: {receipt_data.date}")
        logger.debug(f"Extracted time: {receipt_data.time}")

        # Extract amounts (total, tax, tip, subtotal) - improved extraction
        amounts = self._extract_amounts(raw_text, lines)
        receipt_data.total = amounts.get("total")
        receipt_data.amount = receipt_data.total or amounts.get("subtotal")
        receipt_data.tax = amounts.get("tax")
        receipt_data.tip = amounts.get("tip")
        logger.debug(
            f"Final assignment: total={receipt_data.total}, tax={receipt_data.tax}, amount={receipt_data.amount}"
        )

        # Extract line items
        receipt_data.items = self._extract_items(lines)
        logger.debug(f"Extracted {len(receipt_data.items)} line items: {receipt_data.items[:5]}")

        # Calculate confidence scores (simplified - based on successful extraction)
        receipt_data.confidence_scores = self._calculate_confidence_scores(receipt_data)

        # Final summary log
        logger.debug("\n" + "=" * 60)
        logger.debug("FINAL EXTRACTED RECEIPT DATA:")
        logger.debug("=" * 60)
        logger.debug(f"  Amount: {receipt_data.amount}")
        logger.debug(f"  Total: {receipt_data.total}")
        logger.debug(f"  Tax: {receipt_data.tax}")
        logger.debug(f"  Tip: {receipt_data.tip}")
        logger.debug(f"  Date: {receipt_data.date}")
        logger.debug(f"  Time: {receipt_data.time}")
        logger.debug(f"  Restaurant: {receipt_data.restaurant_name}")
        logger.debug(f"  Address: {receipt_data.restaurant_address}")
        logger.debug(f"  Phone: {receipt_data.restaurant_phone}")
        logger.debug(f"  Website: {receipt_data.restaurant_website}")
        logger.debug(f"  Items: {len(receipt_data.items)} items")
        logger.debug(f"  Confidence Scores: {receipt_data.confidence_scores}")
        logger.debug("=" * 60)

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
                logger.debug(f"Skipping line '{line_stripped}' (contains skip word: {matched_words})")
                continue

            # Skip lines matching exclude patterns
            if any(re.match(pattern, line_stripped, re.IGNORECASE) for pattern in exclude_patterns):
                logger.debug(f"Skipping line '{line_stripped}' (matches exclude pattern)")
                continue

            # Skip lines that are mostly numbers or amounts
            if re.search(r"^\$?\s*\d+\.\d{2}", line_stripped) and len(re.sub(r"[\d\s\$\.]", "", line_stripped)) < 3:
                logger.debug(f"Skipping line '{line_stripped}' (mostly numbers/amount)")
                continue

            # Must have at least some letters (restaurant names have letters)
            if not re.search(r"[a-zA-Z]{2,}", line_stripped):
                logger.debug(f"Skipping line '{line_stripped}' (no letters found)")
                continue

            # Skip lines that look like addresses (street addresses, city/state/zip)
            # Check for address patterns: starts with number + street type, or city/state/zip pattern
            if re.match(r"^\d+\s+[A-Z]\s+FM\s+\d+", line_stripped, re.IGNORECASE):
                logger.debug(f"Skipping line '{line_stripped}' (address pattern: FM road)")
                continue
            if re.match(
                r"^\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Circle|Cir|Place|Pl|FM)\s*\d*",
                line_stripped,
                re.IGNORECASE,
            ):
                logger.debug(f"Skipping line '{line_stripped}' (address pattern: street address)")
                continue
            if re.match(r"^[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}", line_stripped):
                logger.debug(f"Skipping line '{line_stripped}' (address pattern: city/state/zip)")
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
                    logger.debug(f"Extracted restaurant name (with indicator): '{name}' from line '{line_stripped}'")
                    if location_number:
                        logger.debug(f"Extracted location number: '{location_number}'")
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
                logger.debug(f"Skipping line '{line_stripped}' (fallback: address pattern: FM road)")
                continue
            if re.match(
                r"^\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Circle|Cir|Place|Pl|FM)\s*\d*",
                line_stripped,
                re.IGNORECASE,
            ):
                logger.debug(f"Skipping line '{line_stripped}' (fallback: address pattern: street address)")
                continue
            if re.match(r"^[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}", line_stripped):
                logger.debug(f"Skipping line '{line_stripped}' (fallback: address pattern: city/state/zip)")
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
                logger.debug(f"Extracted restaurant name (fallback): '{name}' from line '{line_stripped}'")
                if location_number:
                    logger.debug(f"Extracted location number (fallback): '{location_number}'")
                return name, location_number

        logger.debug("No restaurant name found in first 10 lines")
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
                logger.debug(f"Skipping line {idx} (empty or too short): '{line_stripped}'")
                continue

            # Skip lines with skip words
            skip_word_found = any(word in line_lower for word in skip_words)
            if skip_word_found:
                logger.debug(f"Skipping line {idx} (contains skip word): '{line_stripped}'")
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
                logger.debug(f"Stopping address extraction at line {idx} (menu item with quantity): '{line_stripped}'")

            # Check for lines with amounts at the end (menu items with prices)
            if not is_menu_item and re.search(r"\$\d+\.\d{2}\s*$", line_stripped):
                # But exclude if it's clearly an address (has state abbreviation and zip)
                if not re.search(r"[A-Z]{2}\s+\d{5}", line_stripped):
                    is_menu_item = True
                    logger.debug(f"Stopping address extraction at line {idx} (menu item with price): '{line_stripped}'")

            # Check menu item indicator patterns
            if not is_menu_item:
                for pattern in menu_item_indicators:
                    if re.match(pattern, line_stripped):
                        is_menu_item = True
                        logger.debug(
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
                        logger.debug(
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
                        logger.debug(f"Found FM address pattern at line {idx}: '{line_stripped}'")

            if not is_address_line:
                # Check if line contains address indicators (including "fm")
                if any(indicator in line_lower for indicator in address_indicators):
                    is_address_line = True
                    if "fm" in line_lower:
                        logger.debug(f"Found address via FM indicator at line {idx}: '{line_stripped}'")

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
                logger.debug(f"Found address line {idx}: '{line_stripped}'")

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
            logger.debug(f"Extracted restaurant address: '{combined_address}'")
            return combined_address

        logger.debug("No restaurant address found in first 20 lines")
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
                        logger.debug(f"Skipping phone-like pattern (all same digits): '{phone}' from line {idx}")
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
                            logger.debug(f"Skipping phone-like pattern (invalid area code): '{phone}' from line {idx}")
                            continue
                        # Format as (XXX) XXX-XXXX for consistency
                        formatted_phone = f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
                        logger.debug(
                            f"Extracted restaurant phone: '{formatted_phone}' from line {idx}: '{line_stripped}'"
                        )
                        return formatted_phone
                    elif len(digits_only) == 11 and digits_only[0] == "1":
                        # US number with country code - remove leading 1
                        digits_only = digits_only[1:]
                        # Validate area code
                        if digits_only[0] in ["0", "1"]:
                            logger.debug(f"Skipping phone-like pattern (invalid area code): '{phone}' from line {idx}")
                            continue
                        formatted_phone = f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
                        logger.debug(
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

        logger.debug("No restaurant phone found in first 30 lines")
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
                    logger.debug(f"Extracted restaurant phone from raw text: '{formatted_phone}'")
                    return formatted_phone
                elif len(digits_only) == 11 and digits_only[0] == "1":
                    # US number with country code - remove leading 1
                    digits_only = digits_only[1:]
                    if digits_only[0] in ["0", "1"]:
                        continue
                    formatted_phone = f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
                    logger.debug(f"Extracted restaurant phone from raw text (with country code): '{formatted_phone}'")
                    return formatted_phone

        logger.debug("No restaurant phone found in raw text")
        return None

    def _extract_restaurant_website(self, lines: list[str]) -> str | None:
        """Extract restaurant website from receipt lines."""
        if not lines:
            return None

        website_patterns = [
            r"https?://(?:www\.)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}",
            r"www\.([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}",
        ]

        for line in lines[:20]:
            line_stripped = line.strip()
            if "@" in line_stripped and "www" not in line_stripped.lower():
                continue

            for pattern in website_patterns:
                match = re.search(pattern, line_stripped, re.IGNORECASE)
                if match:
                    website = match.group(0).strip()
                    if not website.startswith(("http://", "https://")):
                        website = "https://" + website
                    return website.lower()

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

                        logger.debug(f"Extracted time from date+time pattern: '{time_str}'")
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

                        logger.debug(f"Extracted time from standalone pattern: '{time_str}'")
                        return time_str
                except (ValueError, IndexError):
                    continue

        logger.debug("No time found in receipt text")
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
                except Exception:
                    continue

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
                                        logger.debug(
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
                        logger.debug(f"Found keyword '{keyword}' on line {idx}: '{line_stripped}'")
                        # Found keyword-only line, check next line for amount
                        if idx + 1 < len(lines):
                            next_line = lines[idx + 1]
                            logger.debug(f"  Checking next line {idx+1} for amount: '{next_line.strip()}'")
                            # Try all amount patterns on the next line
                            for pattern_idx, pattern_check in enumerate(amount_patterns):
                                amount_match = re.search(pattern_check, next_line)
                                if amount_match:
                                    logger.debug(f"    Pattern {pattern_idx} matched: {amount_match.group(0)}")
                                    try:
                                        amount_str = (
                                            amount_match.group(1).replace(",", "").replace(" ", "").replace(",", ".")
                                        )
                                        if "," in amount_str and "." not in amount_str:
                                            amount_str = amount_str.replace(",", ".")
                                        amount = Decimal(amount_str)
                                        logger.debug(f"    Parsed amount: {amount}")

                                        # Filter out phone numbers
                                        if amount >= 100 and amount < 1000 and "." not in amount_match.group(0):
                                            logger.debug("    Skipped (phone number filter)")
                                            continue

                                        # Filter reasonable amounts
                                        if 0.01 <= amount <= 10000:
                                            # Pattern 2 (next-line matching) is more accurate than Pattern 1,
                                            # so always override Pattern 1's value when we find a labeled amount
                                            amounts[amount_type] = amount
                                            logger.debug(
                                                f"Found labeled {amount_type}: ${amount} "
                                                f"(keyword '{keyword}' on line {idx}='{line_stripped}', "
                                                f"amount on line {idx+1}='{next_line.strip()}')"
                                            )
                                            break  # Found amount for this keyword, move to next keyword
                                        else:
                                            logger.debug("    Skipped (outside range)")
                                    except (InvalidOperation, ValueError) as e:
                                        logger.debug(f"    Error parsing amount: {e}")
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

        logger.debug(f"Scanning {len(lines)} lines for amounts using {len(amount_patterns)} patterns")
        for idx, line in enumerate(lines):
            # Skip lines that are clearly phone numbers
            if any(re.search(pattern, line) for pattern in phone_patterns):
                logger.debug(f"  Line {idx}: Skipping line with phone number pattern: '{line[:80]}'")
                continue

            for pattern_idx, pattern in enumerate(amount_patterns):
                matches_list = list(re.finditer(pattern, line))
                if matches_list:
                    logger.debug(
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
                                logger.debug(f"    -> Skipped ${amount} (likely phone number part) from '{line[:60]}'")
                                continue
                            # Also skip standalone 3-digit numbers (very likely phone area codes)
                            # unless they're clearly part of a price (have $ sign or are near price keywords)
                            if not re.search(r"\$|price|cost|amount|total|tax|tip", line_context, re.IGNORECASE):
                                logger.debug(
                                    f"    -> Skipped ${amount} (standalone 3-digit number, likely phone) from '{line[:60]}'"
                                )
                                continue

                        # Filter reasonable amounts (0.01 to 10000)
                        if 0.01 <= amount <= 10000:
                            all_amounts.append((amount, idx, line.lower()))
                            logger.debug(f"    -> Extracted amount: ${amount} from '{match.group(0)}'")
                        else:
                            logger.debug(f"    -> Skipped amount ${amount} (outside reasonable range)")
                    except (InvalidOperation, ValueError) as e:
                        logger.debug(f"    -> Failed to parse amount from '{match.group(0)}': {e}")
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
            except Exception:
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
        logger.debug("=" * 60)
        logger.debug("AMOUNT EXTRACTION DEBUG")
        logger.debug("=" * 60)
        logger.debug(f"Found {len(all_amounts)} total amounts in receipt:")
        for amount, idx, line_text in all_amounts[:20]:  # Show first 20
            logger.debug(f"  Line {idx}: ${amount} - '{line_text[:60]}'")
        if len(all_amounts) > 20:
            logger.debug(f"  ... and {len(all_amounts) - 20} more amounts")

        logger.debug("\nExtracted labeled amounts:")
        logger.debug(f"  Total: {amounts['total']}")
        logger.debug(f"  Tax: {amounts['tax']}")
        logger.debug(f"  Tip: {amounts['tip']}")
        logger.debug(f"  Subtotal: {amounts['subtotal']}")
        logger.debug("=" * 60)

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
            r"^trouble\s+viewing",  # Email footer text
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
            "trouble",
            "viewing",
            "email",
            "morgan",
            "kiosk",  # Common receipt metadata
        }

        # Find where items actually start by looking for menu item patterns
        # Menu items typically have patterns like:
        # - "Classic - Mixed Plate"
        # - "1x DR PEPPER"
        # - Lines with prices at the end
        start_idx = None
        for idx, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean:
                continue

            # Look for menu item indicators
            # Pattern 1: Item with dash (e.g., "Classic - Mixed Plate")
            if re.search(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+-\s+[A-Z]", line_clean):
                start_idx = idx
                logger.debug(f"Found menu items starting at line {idx}: '{line_clean[:60]}'")
                break

            # Pattern 2: Quantity x Item (e.g., "1x DR PEPPER")
            if re.match(r"^\d+x\s+[A-Z]", line_clean, re.IGNORECASE):
                start_idx = idx
                logger.debug(f"Found menu items starting at line {idx}: '{line_clean[:60]}'")
                break

            # Pattern 3: Line with price at end (but not totals)
            if re.search(r"\$\d+\.\d{2}\s*$", line_clean) and not re.match(
                r"^(total|tax|tip|subtotal)", line_clean, re.IGNORECASE
            ):
                # Check if it looks like an item (has letters, reasonable price)
                price_match = re.search(r"\$(\d+\.\d{2})\s*$", line_clean)
                if price_match:
                    try:
                        price_val = Decimal(price_match.group(1))
                        if 0.01 <= price_val <= 1000:  # Reasonable item price
                            item_part = line_clean[: price_match.start()].strip()
                            if len(item_part) >= 3 and re.search(r"[a-zA-Z]{2,}", item_part):
                                start_idx = idx
                                logger.debug(f"Found menu items starting at line {idx}: '{line_clean[:60]}'")
                                break
                    except (InvalidOperation, ValueError):
                        pass

        # If we didn't find a clear start, use a conservative default
        if start_idx is None:
            # Skip more lines for email headers (up to 20 lines)
            start_idx = min(20, len(lines))
            logger.debug(f"No clear menu item start found, using default start_idx={start_idx}")

        # Items end before totals (usually last 5-7 lines)
        end_idx = max(len(lines) - 7, start_idx)

        logger.debug(f"Extracting items from lines {start_idx} to {end_idx} (out of {len(lines)} total lines)")

        for line in lines[start_idx:end_idx]:
            line_clean = line.strip()
            if not line_clean:
                continue

            line_lower = line_clean.lower()

            # Skip if matches skip patterns
            if any(re.match(pattern, line_clean, re.IGNORECASE) for pattern in skip_patterns):
                logger.debug(f"Skipping item line (matches skip pattern): '{line_clean[:60]}'")
                continue

            # Skip if contains skip words (use word boundaries to avoid false positives)
            line_words = set(re.findall(r"\b\w+\b", line_lower))
            skip_words_set = set(skip_words)
            if line_words & skip_words_set:
                logger.debug(f"Skipping item line (contains skip word): '{line_clean[:60]}'")
                continue

            # Skip time patterns
            if re.match(r"^\d{1,2}:\d{2}\s*(AM|PM|am|pm)?$", line_clean, re.IGNORECASE):
                continue

            # Skip phone numbers
            if re.search(r"\(\d{3}\)\s*\d{3}[-.]?\d{4}", line_clean):
                logger.debug(f"Skipping item line (phone number): '{line_clean[:60]}'")
                continue

            # Skip addresses (city, state, zip pattern)
            if re.search(r"[A-Z]{2}\s+\d{5}", line_clean):
                logger.debug(f"Skipping item line (address): '{line_clean[:60]}'")
                continue

            # Skip restaurant name patterns (if we already extracted it)
            # Lines that are just restaurant names or location numbers
            if re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+\d+$", line_clean):  # "Hawaiian Bros 0033"
                logger.debug(f"Skipping item line (restaurant name with number): '{line_clean[:60]}'")
                continue

            # Stop extracting items when we hit payment/transaction info
            payment_keywords = [
                "input type",
                "emv",
                "chip",
                "read",
                "visa",
                "credit",
                "debit",
                "mastercard",
                "amex",
                "transaction",
                "authorization",
                "approved",
                "payment",
                "card",
                "terminal",
                "approval code",
                "payment id",
            ]
            if any(keyword in line_lower for keyword in payment_keywords):
                logger.debug(f"Stopping item extraction at payment info: '{line_clean[:60]}'")
                break

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
            item_name = re.sub(r"^x\s+", "", item_name, flags=re.IGNORECASE)  # Remove leading "x" prefix
            item_name = re.sub(r"\s+", " ", item_name).strip()  # Normalize whitespace

            # Must have at least 3 characters and some letters
            if len(item_name) >= 3 and re.search(r"[a-zA-Z]{2,}", item_name):
                if item_name.lower() not in ["item", "description", "qty", "quantity", "price", "served", "by"]:
                    items.append(item_name)
                    logger.debug(f"Extracted item: '{item_name}' from line '{line_clean[:60]}'")

        logger.debug(f"Extracted {len(items)} items total")
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

    def _parse_bank_statement(self, text: str, lines: list[str]) -> ReceiptData:
        """Parse bank statement data to extract transaction information.

        Args:
            text: Full text content
            lines: List of text lines

        Returns:
            ReceiptData object with parsed fields
        """
        receipt_data = ReceiptData(raw_text=text)

        # Extract transactions (date, merchant, amount pairs)
        transactions = self._extract_transactions(lines)

        # Find the best transaction (prefer restaurant-like merchants)
        best_transaction = self._find_best_transaction(transactions)

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
                    except Exception:
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
                cleaned = re.sub(r"\s+", " ", cleaned).strip()

                # Remove common bank statement artifacts
                cleaned = re.sub(r"^(PUR|DEBIT|CREDIT|ACH|POS|CHECK)\s*", "", cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r"\s*\d{4,}.*$", "", cleaned)  # Remove account numbers at end

                if len(cleaned) > 2 and len(cleaned) < 100:
                    # Clean up common suffixes
                    cleaned = re.sub(
                        r"\s+(INC|LLC|CORP|RESTAURANT|REST|CAFE|GRILL).*$", "", cleaned, flags=re.IGNORECASE
                    )
                    return cleaned.strip()

        # Fallback: look for restaurant-like names in the text
        name_result = self._extract_restaurant_name(lines)
        if isinstance(name_result, tuple):
            return name_result[0]  # Return just the name for bank statements
        return name_result

    def _extract_transactions(self, lines: list[str]) -> list[dict[str, Any]]:
        """Extract transaction data from bank statement lines.

        Args:
            lines: List of text lines from bank statement

        Returns:
            List of transaction dictionaries with 'date', 'merchant', 'amount' keys
        """
        transactions: list[dict[str, Any]] = []
        date_pattern = r"(\d{1,2}[/-]\d{1,2}[/-]?\d{0,4})"
        amount_pattern = r"[-\(]?\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\)?"

        for line in lines:
            # Skip header lines
            if any(
                word in line.lower() for word in ["date", "description", "amount", "balance", "transaction", "account"]
            ):
                continue

            # Look for lines with both date and amount
            date_match = re.search(date_pattern, line)
            amount_match = re.search(amount_pattern, line)

            if date_match and amount_match:
                try:
                    # Extract date
                    date_str = date_match.group(1)
                    parsed_date = None
                    for fmt in [
                        "%m/%d/%Y",
                        "%d/%m/%Y",
                        "%m-%d-%Y",
                        "%d-%m-%Y",
                        "%m/%d/%y",
                        "%d/%m/%y",
                        "%m/%d",
                        "%d/%m",
                    ]:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            if parsed_date.year < 2000:
                                parsed_date = parsed_date.replace(year=datetime.now().year)
                            break
                        except ValueError:
                            continue

                    # Extract amount
                    amount_str = amount_match.group(1).replace(",", "")
                    amount = Decimal(amount_str)

                    # Extract merchant name (text between date and amount)
                    date_start = date_match.start()
                    amount_start = amount_match.start()
                    merchant = line[date_start + len(date_match.group()) : amount_start].strip()
                    merchant = re.sub(r"^(PUR|DEBIT|CREDIT|ACH|POS|CHECK)\s*", "", merchant, flags=re.IGNORECASE)
                    merchant = re.sub(r"\s*\d{4,}.*$", "", merchant)  # Remove account numbers
                    merchant = re.sub(r"\s+", " ", merchant).strip()

                    if parsed_date and 0.01 <= amount <= 10000 and len(merchant) > 2:
                        transactions.append(
                            {
                                "date": parsed_date,
                                "merchant": merchant if len(merchant) < 100 else merchant[:100],
                                "amount": amount,
                            }
                        )
                except (ValueError, InvalidOperation):
                    continue

        return transactions

    def _find_best_transaction(self, transactions: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Find the best transaction from a list, prioritizing restaurant-like merchants.

        Args:
            transactions: List of transaction dictionaries

        Returns:
            Best transaction dictionary or None
        """
        if not transactions:
            return None

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

        # Score transactions (higher score = more likely to be a restaurant)
        scored_transactions: list[tuple[dict[str, Any], float]] = []
        for trans in transactions:
            score = 0.0
            merchant_lower = trans.get("merchant", "").lower()

            # Check for restaurant keywords
            for keyword in restaurant_keywords:
                if keyword in merchant_lower:
                    score += 2.0

            # Prefer recent transactions
            if trans.get("date"):
                days_ago = (datetime.now() - trans["date"]).days
                if days_ago <= 30:
                    score += 1.0
                elif days_ago <= 90:
                    score += 0.5

            # Prefer reasonable meal amounts ($5-$200)
            amount = trans.get("amount", Decimal(0))
            if 5 <= amount <= 200:
                score += 1.0
            elif 200 < amount <= 500:
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


def format_output_text(receipt_data: ReceiptData) -> str:
    """Format receipt data as human-readable text.

    Args:
        receipt_data: ReceiptData object

    Returns:
        Formatted text string
    """
    lines = []
    lines.append("=" * 60)
    lines.append("RECEIPT EXTRACTION RESULTS")
    lines.append("=" * 60)
    lines.append("")

    if receipt_data.restaurant_name:
        restaurant_display = receipt_data.restaurant_name
        if receipt_data.restaurant_location_number:
            restaurant_display += f" ({receipt_data.restaurant_location_number})"
        lines.append(f"Restaurant: {restaurant_display}")
    else:
        lines.append("Restaurant: (not found)")

    if receipt_data.restaurant_address:
        lines.append(f"Address: {receipt_data.restaurant_address}")
    if receipt_data.restaurant_location_number:
        lines.append(f"Location Number: {receipt_data.restaurant_location_number}")
    if receipt_data.restaurant_phone:
        lines.append(f"Phone: {receipt_data.restaurant_phone}")
    if receipt_data.restaurant_website:
        lines.append(f"Website: {receipt_data.restaurant_website}")

    if receipt_data.date:
        # Combine date and time if time is available
        if receipt_data.time:
            # Parse time string (format: "HH:MM AM/PM" or "HH:MM")
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
                        # Combine date and time
                        combined_datetime = receipt_data.date.replace(hour=hour, minute=minute, second=0)
                        lines.append(f"Date/Time: {combined_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                    else:
                        lines.append(f"Date/Time: {receipt_data.date.strftime('%Y-%m-%d')} {time_str}")
                else:
                    # Try parsing 24-hour format
                    time_part = re.search(r"(\d{1,2}):(\d{2})", time_str)
                    if time_part:
                        hour = int(time_part.group(1))
                        minute = int(time_part.group(2))
                        combined_datetime = receipt_data.date.replace(hour=hour, minute=minute, second=0)
                        lines.append(f"Date/Time: {combined_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                    else:
                        lines.append(f"Date/Time: {receipt_data.date.strftime('%Y-%m-%d')} {time_str}")
            except (ValueError, AttributeError):
                # Fallback: just append time string
                lines.append(f"Date/Time: {receipt_data.date.strftime('%Y-%m-%d')} {time_str}")
        else:
            # No time available, just show date
            lines.append(f"Date: {receipt_data.date.strftime('%Y-%m-%d')}")
    else:
        lines.append("Date: (not found)")

    if receipt_data.amount:
        lines.append(f"Amount: ${receipt_data.amount:.2f}")
    else:
        lines.append("Amount: (not found)")

    if receipt_data.total:
        lines.append(f"Total: ${receipt_data.total:.2f}")
    if receipt_data.tax:
        lines.append(f"Tax: ${receipt_data.tax:.2f}")
    if receipt_data.tip:
        lines.append(f"Tip: ${receipt_data.tip:.2f}")

    if receipt_data.items:
        lines.append("")
        lines.append("Items:")
        for item in receipt_data.items:
            lines.append(f"  - {item}")

    if receipt_data.confidence_scores:
        lines.append("")
        lines.append("Confidence Scores:")
        for field, score in receipt_data.confidence_scores.items():
            lines.append(f"  {field}: {score:.1%}")

    lines.append("")
    lines.append("=" * 60)
    lines.append("RAW TEXT (first 500 chars)")
    lines.append("=" * 60)
    lines.append(receipt_data.raw_text[:500])
    if len(receipt_data.raw_text) > 500:
        lines.append("...")
        lines.append(f"(truncated, total length: {len(receipt_data.raw_text)} characters)")

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
  python scripts/extract_receipt.py receipt.jpg
  python scripts/extract_receipt.py receipt.pdf --output-format json
  python scripts/extract_receipt.py receipt.png --tesseract-cmd /usr/local/bin/tesseract
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
        "--tesseract-cmd",
        type=str,
        default=None,
        help="Optional path to Tesseract binary (auto-detected if not set)",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.7,
        help="Confidence threshold (default: 0.7)",
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

    # Validate file exists
    file_path = Path(args.file_path)
    if not file_path.exists():
        logger.error(f"File not found: {args.file_path}")
        return 1

    try:
        # Initialize OCR service
        ocr_service = StandaloneOCRService(
            tesseract_cmd=args.tesseract_cmd,
            confidence_threshold=args.confidence_threshold,
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
        logger.error(f"Unexpected error: {e}", exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
