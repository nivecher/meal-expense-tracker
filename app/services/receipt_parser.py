"""Unified receipt parser for extracting structured data from OCR text.

This module provides a shared ReceiptParser class that contains all receipt parsing logic
used by both the web application and standalone scripts. It has no dependencies on Flask
or AWS services, making it reusable across different contexts.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class ReceiptParser:
    """Unified receipt parser with all extraction methods."""

    def parse_receipt_data(self, raw_text: str, receipt_data: Any) -> Any:
        """Parse receipt data from extracted text using section-based approach.

        This method identifies sections in the receipt and extracts data from each section.
        This approach is more robust and handles various receipt formats.

        Args:
            raw_text: Raw text extracted from OCR

        Returns:
            ReceiptData object with parsed fields
        """
        receipt_data.raw_text = raw_text
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
            return self._parse_bank_statement(raw_text, lines, receipt_data)

        # Section-based parsing: Identify sections and extract data from each
        sections = self._identify_sections(lines)
        logger.debug(f"Identified {len(sections)} sections: {list(sections.keys())}")

        # Extract data from each section
        extracted_data = {}
        for section_name, section_lines in sections.items():
            logger.debug(f"Processing section '{section_name}' with {len(section_lines)} lines")
            section_data = self._extract_from_section(section_name, section_lines, lines, raw_text)
            if section_data:
                extracted_data[section_name] = section_data
                logger.debug(f"Extracted from '{section_name}': {section_data}")

        # Map extracted section data to ReceiptData fields
        receipt_data = self._map_section_data_to_receipt(extracted_data, receipt_data)

        # Fallback: If section-based parsing didn't extract key fields, use legacy parsing
        # Run legacy parser if restaurant_name is missing, OR if items/total are missing
        if not receipt_data.restaurant_name or not receipt_data.items or not receipt_data.total:
            logger.warning("Section-based parsing produced incomplete results, falling back to legacy parsing")
            receipt_data = self._parse_receipt_data_legacy(raw_text, lines, receipt_data)

        # Calculate confidence scores
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
        logger.debug(f"  Location #: {receipt_data.restaurant_location_number}")
        logger.debug(f"  Address: {receipt_data.restaurant_address}")
        logger.debug(f"  Phone: {receipt_data.restaurant_phone}")
        logger.debug(f"  Website: {receipt_data.restaurant_website}")
        logger.debug(f"  Check #: {receipt_data.check_number}")
        logger.debug(f"  Table #: {receipt_data.table_number}")
        logger.debug(f"  Server: {receipt_data.server_name}")
        logger.debug(f"  Customer: {receipt_data.customer_name}")
        logger.debug(f"  Items: {len(receipt_data.items)} items")
        logger.debug(f"  Confidence Scores: {receipt_data.confidence_scores}")
        logger.debug("=" * 60)

        return receipt_data

    def _parse_receipt_data_legacy(self, raw_text: str, lines: list[str], receipt_data: Any) -> Any:
        """Legacy parsing method as fallback when section-based parsing fails.

        This uses the original line-by-line extraction approach.

        Args:
            raw_text: Raw text extracted from OCR
            lines: List of text lines
            receipt_data: Partially populated ReceiptData object

        Returns:
            ReceiptData object with parsed fields
        """
        # Extract restaurant name - overwrite if current value looks incorrect (e.g., date/time)
        current_name = receipt_data.restaurant_name
        # Check if current name looks like a date/time (common mistake)
        is_incorrect_name = False
        if current_name:
            # Check if it matches date/time patterns
            date_time_patterns = [
                r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+\d{1,2}:\d{2}\s*(AM|PM|am|pm)",  # "07/23/2022 07:27 PM"
                r"^\d{1,2}:\d{2}\s*(AM|PM|am|pm)$",  # "07:27 PM"
                r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$",  # "07/23/2022"
            ]
            for pattern in date_time_patterns:
                if re.match(pattern, current_name, re.IGNORECASE):
                    is_incorrect_name = True
                    logger.debug(f"Current restaurant name '{current_name}' looks like date/time, will overwrite")
                    break

        if not receipt_data.restaurant_name or is_incorrect_name:
            name_result = self._extract_restaurant_name(lines)
            receipt_data.restaurant_name, receipt_data.restaurant_location_number = name_result

        if not receipt_data.restaurant_address:
            receipt_data.restaurant_address = self._extract_restaurant_address(lines)

        if not receipt_data.restaurant_phone:
            receipt_data.restaurant_phone = self._extract_restaurant_phone(lines)
            if not receipt_data.restaurant_phone:
                receipt_data.restaurant_phone = self._extract_restaurant_phone_from_text(raw_text)

        if not receipt_data.restaurant_website:
            receipt_data.restaurant_website = self._extract_restaurant_website(lines)

        if not receipt_data.date:
            receipt_data.date = self._extract_date(raw_text)
        if not receipt_data.time:
            receipt_data.time = self._extract_time(raw_text, lines)

        # Safely check for subtotal (may not exist in web app ReceiptData)
        subtotal = getattr(receipt_data, "subtotal", None)
        if not subtotal or not receipt_data.tax or not receipt_data.total:
            amounts = self._extract_amounts(raw_text, lines)
            # Only set subtotal if the attribute exists
            if hasattr(receipt_data, "subtotal"):
                if not receipt_data.subtotal:
                    receipt_data.subtotal = amounts.get("subtotal")
            if not receipt_data.tax:
                receipt_data.tax = amounts.get("tax")
            if not receipt_data.tip:
                receipt_data.tip = amounts.get("tip")
            if not receipt_data.total:
                receipt_data.total = amounts.get("total")
            if not receipt_data.amount:
                # Use subtotal if available, otherwise just total
                subtotal_val = getattr(receipt_data, "subtotal", None)
                receipt_data.amount = receipt_data.total or subtotal_val

        if not receipt_data.server_name:
            receipt_data.server_name = self._extract_server_name(lines)
        if not receipt_data.customer_name or not receipt_data.check_number:
            customer, check = self._extract_customer_and_check(lines)
            if not receipt_data.customer_name:
                receipt_data.customer_name = customer
            if not receipt_data.check_number:
                receipt_data.check_number = check
        if not receipt_data.table_number:
            receipt_data.table_number = self._extract_table_number(lines)

        if not receipt_data.items or len(receipt_data.items) == 0:
            receipt_data.items = self._extract_items(lines, restaurant_name=receipt_data.restaurant_name)

        return receipt_data

    def _identify_sections(self, lines: list[str]) -> dict[str, list[str]]:
        """Identify sections in the receipt and group lines by section.

        Sections identified:
        - header: Restaurant name, address, phone, website (usually first 10-15 lines)
        - order_info: Date, time, check #, table #, server, customer (usually after header)
        - items: Menu items with prices (middle section)
        - totals: Subtotal, tax, tip, total, amount paid (usually near end)
        - payment: Payment method, card info, transaction details (after totals)
        - footer: Thank you messages, promotional text (end of receipt)

        Args:
            lines: List of text lines from receipt

        Returns:
            Dictionary mapping section names to lists of lines in that section
        """
        sections: dict[str, list[str]] = {
            "header": [],
            "order_info": [],
            "items": [],
            "totals": [],
            "payment": [],
            "footer": [],
        }

        if not lines:
            return sections

        # Keywords to identify section boundaries
        order_info_keywords = ["check", "table", "server", "date", "time", "ordered", "customer", "guest"]
        items_keywords = ["description", "qty", "quantity", "item", "price", "menu"]
        totals_keywords = [
            "subtotal",
            "sub total",
            "tax",
            "tip",
            "gratuity",
            "total",
            "amount",
            "paid",
            "due",
            "balance",
        ]
        payment_keywords = [
            "visa",
            "mastercard",
            "amex",
            "credit",
            "debit",
            "card",
            "payment",
            "transaction",
            "authorization",
            "approval",
            "emv",
            "chip",
            "tap",
        ]
        footer_keywords = ["thank", "visit", "gracias", "join", "club", "sign up", "automatically generated"]

        current_section = "header"
        header_end_idx = min(15, len(lines))  # Header typically first 15 lines
        items_started = False
        totals_started = False
        payment_started = False

        for idx, line in enumerate(lines):
            line_lower = line.lower()

            # Skip email headers and common receipt artifacts at the very beginning
            if idx < 10:
                skip_patterns = [
                    "outlook",
                    "from",
                    "to",
                    "subject",
                    "sent",
                    "reply",
                    "no-reply",
                    "receipt for",
                    "receipt from",
                    "thank you for your order",
                ]
                if any(pattern in line_lower for pattern in skip_patterns):
                    continue  # Skip this line entirely

            # Special handling: If this is a price-only line and previous line was an item name,
            # keep it in the items section (prices can be on separate lines from item names)
            is_price_only = bool(re.match(r"^\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*$", line.strip()))
            if is_price_only and items_started and idx > 0:
                prev_line = lines[idx - 1].strip()
                # Check if previous line looks like an item name (not a totals label)
                prev_looks_like_item = (
                    re.search(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+-\s+[A-Z])?", prev_line)
                    and not any(keyword in prev_line.lower() for keyword in totals_keywords)
                    and not re.match(
                        r"^\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*$", prev_line
                    )  # Previous line is not also a price
                )
                if prev_looks_like_item:
                    # This price belongs to the previous item, keep it in items section
                    current_section = "items"
                    sections[current_section].append(line)
                    continue

            # Identify section transitions (simplified logic)
            # Check for totals keywords first (highest priority after items started)
            if items_started and not totals_started and any(keyword in line_lower for keyword in totals_keywords):
                totals_started = True
                current_section = "totals"
            # Check for payment keywords (after totals)
            elif totals_started and not payment_started and any(keyword in line_lower for keyword in payment_keywords):
                payment_started = True
                current_section = "payment"
            # Check for footer keywords
            elif any(keyword in line_lower for keyword in footer_keywords):
                current_section = "footer"
            # Check for items (before totals)
            elif not totals_started:
                # Check for table structure (markdown-style tables with |)
                if "|" in line and ("description" in line_lower or "qty" in line_lower or "price" in line_lower):
                    items_started = True
                    current_section = "items"
                # Check for item-like patterns (text followed by price) - more flexible
                elif re.search(r"[A-Z][a-zA-Z\s\-']+", line) and re.search(r"\$\d+\.\d{2}", line):
                    # Make sure it's not a totals line
                    if not any(keyword in line_lower for keyword in totals_keywords):
                        items_started = True
                        current_section = "items"
                    else:
                        totals_started = True
                        current_section = "totals"
                # Check for item keywords
                elif any(keyword in line_lower for keyword in items_keywords):
                    items_started = True
                    current_section = "items"
                # Check for item name patterns (even without price on same line)
                elif re.search(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+-\s+[A-Z])?", line) and not any(
                    keyword in line_lower for keyword in totals_keywords
                ):
                    items_started = True
                    current_section = "items"
                # If we've already started items, continue in items section
                elif items_started:
                    current_section = "items"
                # Check for order info keywords
                elif any(keyword in line_lower for keyword in order_info_keywords):
                    current_section = "order_info"
                # Default: if we're in first 15 lines, it's header, otherwise order_info
                elif idx < header_end_idx:
                    current_section = "header"
                else:
                    current_section = "order_info"
            # After totals started, continue in totals or payment
            elif totals_started and not payment_started:
                if any(keyword in line_lower for keyword in payment_keywords):
                    payment_started = True
                    current_section = "payment"
                else:
                    current_section = "totals"
            elif payment_started:
                current_section = "payment"
            # Note: All cases are covered by the above conditions, so no else block needed
            # If none of the conditions match, current_section retains its previous value

            # Add line to appropriate section
            sections[current_section].append(line)

        logger.debug(
            f"Section breakdown: header={len(sections['header'])}, order_info={len(sections['order_info'])}, "
            f"items={len(sections['items'])}, totals={len(sections['totals'])}, "
            f"payment={len(sections['payment'])}, footer={len(sections['footer'])}"
        )

        return sections

    def _extract_from_section(
        self, section_name: str, section_lines: list[str], all_lines: list[str], raw_text: str
    ) -> dict[str, Any]:
        """Extract data from a specific section.

        Args:
            section_name: Name of the section (header, order_info, items, totals, payment, footer)
            section_lines: Lines belonging to this section
            all_lines: All lines from the receipt (for context)
            raw_text: Full raw text (for pattern matching)

        Returns:
            Dictionary of extracted data from this section
        """
        if not section_lines:
            return {}

        extracted: dict[str, Any] = {}

        if section_name == "header":
            # Extract restaurant name, location number, address, phone, website
            name_result = self._extract_restaurant_name(section_lines)
            extracted["restaurant_name"], extracted["restaurant_location_number"] = name_result

            extracted["restaurant_address"] = self._extract_restaurant_address(section_lines)
            extracted["restaurant_phone"] = self._extract_restaurant_phone(section_lines)
            if not extracted["restaurant_phone"]:
                extracted["restaurant_phone"] = self._extract_restaurant_phone_from_text(raw_text)
            extracted["restaurant_website"] = self._extract_restaurant_website(section_lines)

        elif section_name == "order_info":
            # Extract date, time, check #, table #, server, customer
            extracted["date"] = self._extract_date("\n".join(section_lines))
            extracted["time"] = self._extract_time("\n".join(section_lines), section_lines)
            extracted["check_number"] = self._extract_check_number(section_lines)
            extracted["table_number"] = self._extract_table_number(section_lines)
            extracted["server_name"] = self._extract_server_name(section_lines)
            extracted["customer_name"] = self._extract_customer_name(section_lines)

        elif section_name == "items":
            # Extract menu items with prices
            # Get restaurant name from header section if available
            restaurant_name = None
            for line in all_lines[:15]:
                name_result = self._extract_restaurant_name([line])
                if name_result[0]:
                    restaurant_name = name_result[0]
                    break
            extracted["items"] = self._extract_items_from_section(section_lines, restaurant_name)

        elif section_name == "totals":
            # Extract subtotal, tax, tip, total, amount paid
            amounts = self._extract_amounts_from_totals_section(section_lines)
            extracted.update(amounts)

        elif section_name == "payment":
            # Payment info is usually not needed for basic receipt data
            # But we could extract payment method, card type, etc. if needed
            pass

        elif section_name == "footer":
            # Footer usually doesn't contain extractable data
            pass

        # Remove None values
        return {k: v for k, v in extracted.items() if v is not None}

    def _map_section_data_to_receipt(self, extracted_data: dict[str, dict[str, Any]], receipt_data: Any) -> Any:
        """Map extracted section data to ReceiptData fields.

        Args:
            extracted_data: Dictionary of section names to extracted data dictionaries
            receipt_data: Any object to populate

        Returns:
            ReceiptData object with populated fields
        """
        # Map header section data
        if "header" in extracted_data:
            header_data = extracted_data["header"]
            receipt_data.restaurant_name = header_data.get("restaurant_name")
            receipt_data.restaurant_location_number = header_data.get("restaurant_location_number")
            receipt_data.restaurant_address = header_data.get("restaurant_address")
            receipt_data.restaurant_phone = header_data.get("restaurant_phone")
            receipt_data.restaurant_website = header_data.get("restaurant_website")

        # Map order_info section data
        if "order_info" in extracted_data:
            order_data = extracted_data["order_info"]
            receipt_data.date = order_data.get("date")
            receipt_data.time = order_data.get("time")
            receipt_data.check_number = order_data.get("check_number")
            receipt_data.table_number = order_data.get("table_number")
            receipt_data.server_name = order_data.get("server_name")
            receipt_data.customer_name = order_data.get("customer_name")

        # Map items section data
        if "items" in extracted_data:
            receipt_data.items = extracted_data["items"].get("items", [])

        # Map totals section data
        if "totals" in extracted_data:
            totals_data = extracted_data["totals"]
            # Only set subtotal if the attribute exists (web app ReceiptData doesn't have it)
            if hasattr(receipt_data, "subtotal"):
                receipt_data.subtotal = totals_data.get("subtotal")
            receipt_data.tax = totals_data.get("tax")
            receipt_data.tip = totals_data.get("tip")
            receipt_data.total = totals_data.get("total")
            # Use subtotal if available, otherwise just total
            subtotal_val = totals_data.get("subtotal") if hasattr(receipt_data, "subtotal") else None
            receipt_data.amount = totals_data.get("amount") or totals_data.get("total") or subtotal_val

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
            "served",  # "Served by" indicates server name, not restaurant name
        }

        # Patterns to exclude (times, dates, amounts, email addresses, addresses, etc.)
        exclude_patterns = [
            r"^\d{1,2}:\d{2}\s*(AM|PM|am|pm)$",  # Time: "12:55 PM"
            r"^\d{1,2}:\d{2}$",  # Time without AM/PM: "12:55"
            r"^\d+[\s\d:/-]*$",  # Just numbers with separators
            r"^\$?\s*\d+\.\d{2}$",  # Just an amount: "$10.00"
            r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$",  # Date: "10/05/2025"
            r"^\d{4}[/-]\d{1,2}[/-]\d{1,2}$",  # Date: "2025-10-05"
            r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+\d{1,2}:\d{2}\s*(AM|PM|am|pm)",  # Date + Time: "07/23/2022 07:27 PM"
            r"^total|tax|tip|subtotal",  # Common receipt labels
            r"^\d+\s*x\s*\$?\d+",  # Quantity x price
            r"^\d+\s*x\s+[A-Z]",  # Quantity x Item (e.g., "1x DR PEPPER", "2x SALMON")
            r"^table\s+\d+|server\s+\d+|check\s+\d+",  # Table/server/check numbers
            r"^served\s+by\s+",  # "Served by Name" - server information, not restaurant name
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

        # First pass: prioritize lines with restaurant indicators (cafe, restaurant, etc.)
        # This ensures we find restaurant names even if they appear after other lines
        for line in lines[:10]:
            line_lower = line.lower().strip()
            line_stripped = line.strip()

            # Skip empty lines
            if not line_stripped or len(line_stripped) < 3:
                continue

            # Check if this line has restaurant indicators first
            has_restaurant_indicator = any(indicator in line_lower for indicator in restaurant_indicators)
            if not has_restaurant_indicator:
                continue  # Skip lines without indicators in first pass

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

            # If it has restaurant indicators, prioritize it
            if len(name) > 2:
                # Convert all caps to proper case
                name = self._to_proper_case(name)
                logger.debug(f"Extracted restaurant name (with indicator): '{name}' from line '{line_stripped}'")
                logger.debug(f"Location number extracted: '{location_number}'")
                return name, location_number

        # Second pass: check all lines (up to 10) to find restaurant name past email headers
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
                    # Convert all caps to proper case
                    name = self._to_proper_case(name)
                    logger.debug(f"Extracted restaurant name (with indicator): '{name}' from line '{line_stripped}'")
                    logger.debug(f"Location number extracted: '{location_number}'")
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
                # Convert all caps to proper case
                name = self._to_proper_case(name)
                logger.debug(f"Extracted restaurant name (fallback): '{name}' from line '{line_stripped}'")
                logger.debug(f"Location number extracted (fallback): '{location_number}'")
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
                except (ValueError, TypeError, AttributeError) as e:
                    logger.debug(f"Unexpected error parsing date '{date_str}': {e}")
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

    def _extract_check_number(self, lines: list[str]) -> str | None:
        """Extract check number from order info section.

        Args:
            lines: Lines from order info section

        Returns:
            Check number string or None
        """
        for line in lines:
            # Pattern: "Check No: 824686", "Check #32", "Check 32", etc.
            check_match = re.search(r"check\s*(?:no|#)?\s*:?\s*(\d+)", line, re.IGNORECASE)
            if check_match:
                return check_match.group(1)
        return None

    def _extract_customer_name(self, lines: list[str]) -> str | None:
        """Extract customer name from order info section.

        Args:
            lines: Lines from order info section

        Returns:
            Customer name string or None
        """
        for line in lines:
            # Pattern: "Customer: Name" or standalone name after check number
            customer_match = re.search(r"customer\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", line, re.IGNORECASE)
            if customer_match:
                return customer_match.group(1).strip()
        return None

    def _extract_customer_and_check(self, lines: list[str]) -> tuple[str | None, str | None]:
        """Extract customer name and check number from receipt lines.

        Looks for patterns like "Check #32 Name", "Check #32", etc.

        Args:
            lines: List of text lines

        Returns:
            Tuple of (customer_name, check_number) or (None, None)
        """
        for line in lines[:30]:  # Check first 30 lines
            line_clean = line.strip()

            # Pattern: "Check #32 Name" or "Check #32" or "Check 32 Name"
            check_match = re.search(r"check\s*#?\s*(\d+)\s*([A-Z][a-z]+)?", line_clean, re.IGNORECASE)
            if check_match:
                check_number = check_match.group(1)
                customer_name = check_match.group(2).strip() if check_match.group(2) else None

                # If customer name not found in same line, check next line
                if not customer_name:
                    # Check if next line is just a name
                    line_idx = lines.index(line) if line in lines else -1
                    if line_idx >= 0 and line_idx + 1 < len(lines):
                        next_line = lines[line_idx + 1].strip()
                        # Check if next line looks like a name (single capitalized word)
                        if (
                            len(next_line.split()) == 1
                            and next_line[0].isupper()
                            and next_line.isalpha()
                            and len(next_line) >= 2
                        ):
                            customer_name = next_line
                            logger.debug(f"Extracted customer name from next line: '{customer_name}'")

                logger.debug(
                    f"Extracted check number: '{check_number}', customer: '{customer_name}' from line: '{line_clean}'"
                )
                return customer_name, check_number

        return None, None

    def _extract_table_number(self, lines: list[str]) -> str | None:
        """Extract table number from receipt lines.

        Looks for patterns like "Table 12", "Table: 12", "Tbl 5", etc.

        Args:
            lines: List of text lines

        Returns:
            Table number string or None
        """
        for line in lines[:30]:  # Check first 30 lines
            line_clean = line.strip()

            # Pattern 1: "Table 12", "Table: 12", "Table #12"
            table_match = re.search(r"table\s*:?\s*#?\s*(\d+)", line_clean, re.IGNORECASE)
            if table_match:
                table_number = table_match.group(1)
                logger.debug(f"Extracted table number: '{table_number}' from line: '{line_clean}'")
                return table_number

            # Pattern 2: "Tbl 12", "Tbl: 12"
            tbl_match = re.search(r"tbl\s*:?\s*#?\s*(\d+)", line_clean, re.IGNORECASE)
            if tbl_match:
                table_number = tbl_match.group(1)
                logger.debug(f"Extracted table number (tbl): '{table_number}' from line: '{line_clean}'")
                return table_number

        return None

    def _extract_server_name(self, lines: list[str]) -> str | None:
        """Extract server name from receipt lines.

        Looks for patterns like "Server: Name", "Served by Name", etc.

        Args:
            lines: List of text lines

        Returns:
            Server name or None
        """
        for line in lines[:30]:  # Check first 30 lines
            line_clean = line.strip()

            # Pattern 1: "Server: Name" or "Server Name"
            server_match = re.search(r"server\s*:?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]*\.?)*)", line_clean, re.IGNORECASE)
            if server_match:
                server_name = server_match.group(1).strip()
                # Skip if it's just "Kiosk" or "0" or similar
                if server_name.lower() not in ["kiosk", "0", "n/a", "none"]:
                    logger.debug(f"Extracted server name: '{server_name}' from line: '{line_clean}'")
                    return server_name

            # Pattern 2: "Served by Name" or "Served By Name"
            served_by_match = re.search(r"served\s+by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]*\.?)*)", line_clean, re.IGNORECASE)
            if served_by_match:
                server_name = served_by_match.group(1).strip()
                if server_name.lower() not in ["kiosk", "0", "n/a", "none"]:
                    logger.debug(f"Extracted server name (served by): '{server_name}' from line: '{line_clean}'")
                    return server_name

        return None

    def _extract_items_from_section(
        self, section_lines: list[str], restaurant_name: str | None = None
    ) -> list[dict[str, Any]]:
        """Extract items from items section, handling table formats and line formats.

        Args:
            section_lines: Lines from items section
            restaurant_name: Restaurant name to exclude from items

        Returns:
            List of item dictionaries with 'name' and 'price' keys
        """
        items: list[dict[str, Any]] = []

        # Check if this is a table format (markdown-style with |)
        is_table_format = any("|" in line for line in section_lines[:5])

        if is_table_format:
            # Parse table format: | Description | Qty | Price |
            for line in section_lines:
                if "|" not in line:
                    continue
                # Skip header rows
                if re.search(r"description|qty|quantity|price", line, re.IGNORECASE):
                    continue
                # Skip separator rows
                if re.search(r"^[\s\|:\-]+$", line):
                    continue

                # Split by | and extract columns
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2:
                    # Usually: Description, Qty, Price (or Description, Price)
                    item_name = parts[0]
                    # Find price (last column with $ or number)
                    item_price = None
                    for part in reversed(parts):
                        price_match = re.search(r"\$?(\d+\.\d{2})", part)
                        if price_match:
                            try:
                                item_price = Decimal(price_match.group(1))
                                break
                            except (InvalidOperation, ValueError):
                                continue

                    if item_name and len(item_name) > 2:
                        # Skip if it's a totals row
                        if re.search(r"subtotal|tax|tip|total|amount", item_name, re.IGNORECASE):
                            continue
                        items.append({"name": item_name, "price": item_price or Decimal("0.00")})
        else:
            # Parse line format: "Item Name $12.50" or "Item Name 12.50"
            # Also handle cases where price is on the next line
            # Track parent item for grouping sub-items/modifiers
            current_parent_item: dict[str, Any] | None = None

            for idx, line in enumerate(section_lines):
                # Preserve original line to check indentation
                original_line = line
                line_clean = line.strip()
                if not line_clean:
                    continue

                # Skip separator lines
                if self._is_separator_line(line_clean):
                    continue

                # Skip totals rows
                if re.search(r"^subtotal|^tax|^tip|^total|^amount", line_clean, re.IGNORECASE):
                    # Reset parent when we hit totals
                    current_parent_item = None
                    continue

                # Skip lines that are just prices (likely from previous item)
                if re.match(r"^\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*$", line_clean):
                    continue

                # Skip non-item lines: dates, addresses, server info, etc.
                skip_patterns = [
                    r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",  # Date patterns
                    r"^\d{1,2}:\d{2}\s*(AM|PM|am|pm)",  # Time patterns
                    r"^date\s+",  # "Date Sun..." patterns
                    r"^server\s*:|^check\s*#|^ordered\s*:",  # Server/check info
                    r"^[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}",  # City, State ZIP
                    r"^\d+\s+[A-Z]\s+FM\s+\d+",  # FM road addresses
                    r"^\(?\d{3}\)?\s*-?\s*\d{3}\s*-?\s*\d{4}",  # Phone numbers
                    r"^[A-Z][a-z]+\s+Bros\s+\d+$",  # "Hawaiian Bros 0033" pattern
                    r"^[A-Z][a-z]+$",  # Single capitalized word (likely a name like "Morgan")
                ]
                if any(re.search(pattern, line_clean, re.IGNORECASE) for pattern in skip_patterns):
                    # Additional check: skip if line contains date/time together
                    if re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+\d{1,2}:\d{2}", line_clean):
                        continue
                    # Skip single word names (unless they're item-like with dashes)
                    if not re.search(r"-", line_clean) and len(line_clean.split()) == 1 and line_clean[0].isupper():
                        continue
                    continue

                # Check for indentation (leading spaces) to identify sub-items/modifiers
                leading_spaces = len(original_line) - len(original_line.lstrip())
                is_indented = leading_spaces > 0

                # Extract item name and price
                item_match = re.match(r"^(.+?)\s+\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*$", line_clean)
                item_name = None
                item_price = None

                if item_match:
                    # Price on same line
                    item_name = item_match.group(1).strip()
                    price_str = item_match.group(2)
                    try:
                        item_price = Decimal(price_str.replace(",", ""))
                        if not (0.01 <= item_price <= 1000):  # Reasonable price range
                            item_price = None
                    except (InvalidOperation, ValueError):
                        item_price = None
                else:
                    # Check if this looks like an item name (check next line for price)
                    if re.search(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+-\s+[A-Z])?", line_clean):
                        item_name = line_clean
                        # Check next line for price
                        if idx + 1 < len(section_lines):
                            next_line = section_lines[idx + 1].strip()
                            logger.debug(f"Checking next line for price: '{next_line}' (after item: '{item_name}')")
                            price_match = re.match(r"^\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*$", next_line)
                            if price_match:
                                logger.debug(f"Found price match: {price_match.group(0)}")
                                try:
                                    item_price = Decimal(price_match.group(1).replace(",", ""))
                                    logger.debug(f"Parsed price: {item_price}")
                                    if not (0.00 <= item_price <= 1000):  # Reasonable price range (allow $0.00)
                                        logger.debug(f"Price {item_price} outside range, setting to None")
                                        item_price = None
                                    else:
                                        logger.debug(f"Price {item_price} is valid")
                                except (InvalidOperation, ValueError) as e:
                                    logger.debug(f"Error parsing price: {e}")
                                    item_price = None
                            else:
                                logger.debug(f"No price match found on next line: '{next_line}'")
                        else:
                            logger.debug(f"No next line available for item: '{item_name}'")
                        # If no price found, default to $0.00
                        if item_price is None:
                            logger.debug(f"No price found for item '{item_name}', defaulting to $0.00")
                            item_price = Decimal("0.00")

                if item_name:
                    # Check if this is a sub-item/modifier
                    # Modifiers are typically:
                    # 1. Indented (have leading spaces)
                    # 2. Appear immediately after a main item or its modifiers
                    # 3. Have small or no price (< $2.00)
                    # 4. Look like modifiers (start with "No", are short, etc.)

                    is_modifier = False
                    if current_parent_item is not None:
                        # Check if indented (strongest indicator of modifier)
                        if is_indented:
                            is_modifier = True
                        # Check if looks like a modifier pattern (starts with "No")
                        elif line_clean.startswith("No "):
                            is_modifier = True
                        # Check if small price (< $2.00) and short name (likely modifier)
                        elif item_price and item_price < 2.00 and len(line_clean.split()) <= 4:
                            is_modifier = True
                        # Check if no price or $0.00, short name, and appears right after main item
                        # But exclude items that look like separate products (e.g., "Barq's Root Beer")
                        elif (not item_price or item_price == Decimal("0.00")) and len(line_clean.split()) <= 4:
                            # Exclude items that look like product names (contain brand names, etc.)
                            product_indicators = ["root", "beer", "drink", "soda", "coke", "pepsi", "sprite"]
                            if not any(indicator in line_clean.lower() for indicator in product_indicators):
                                is_modifier = True

                    # If this item has a significant price (>= $2.00), it's definitely a main item
                    # Also, if it's a long name and not indented, it's likely a main item
                    is_definitely_main_item = (item_price and item_price >= 2.00) or (
                        len(line_clean.split()) > 4 and not is_indented and not line_clean.startswith("No ")
                    )

                    if is_modifier and current_parent_item is not None and not is_definitely_main_item:
                        # This is a sub-item/modifier - add to parent's modifiers list
                        if "modifiers" not in current_parent_item:
                            current_parent_item["modifiers"] = []
                        modifier_item = {"name": item_name, "price": item_price or Decimal("0.00")}
                        current_parent_item["modifiers"].append(modifier_item)
                        logger.debug(f"Added modifier '{item_name}' to parent '{current_parent_item.get('name')}'")
                    else:
                        # This is a main item - reset parent
                        new_item = {"name": item_name, "price": item_price or Decimal("0.00")}
                        items.append(new_item)
                        current_parent_item = new_item
                        logger.debug(f"Added main item '{item_name}' with price {item_price}")

        # Filter out restaurant name if provided
        if restaurant_name:
            restaurant_lower = restaurant_name.lower()
            items = [
                item
                for item in items
                if item["name"].lower() != restaurant_lower and restaurant_lower not in item["name"].lower()
            ]

        return items

    def _extract_items(self, lines: list[str], restaurant_name: str | None = None) -> list[dict[str, Any]]:
        """Extract line items from receipt with prices.

        Args:
            lines: List of text lines
            restaurant_name: Extracted restaurant name to exclude from items

        Returns:
            List of item dictionaries with 'name' and 'price' keys
        """
        items: list[dict[str, Any]] = []
        skip_patterns = [
            r"^total",
            r"^tax",
            r"^tip",
            r"^subtotal",
            r"^\$?\s*\d+\.\d{2}$",  # Just an amount
            r"^\d+[/-]\d+[/-]\d+",  # Date
            r"^from\s+|^to\s+|^subject\s+",  # Email headers
            r".*@.*",  # Email addresses
            r"^server\s*:|^check\s*#|^ordered\s*:",  # Receipt metadata
            r"^thank\s+you",  # Footer text
            r"^trouble\s+viewing",  # Email footer text
            r"^—+\s*$",  # Separator lines (e.g., "———")
            r"^[-=_]+\s*$",  # Separator lines with dashes/equals/underscores
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
        }

        # Track if we're in a metadata section (after "Check #", "Server:", "Ordered:")
        in_metadata_section = False

        # Use separator detection to find item section boundaries
        start_idx, end_idx = self._find_section_boundaries(lines)

        logger.debug(f"Extracting items from lines {start_idx} to {end_idx} (out of {len(lines)} total lines)")

        for line in lines[start_idx:end_idx]:
            line_clean = line.strip()
            if not line_clean:
                continue

            line_lower = line_clean.lower()

            # Skip separator lines
            if self._is_separator_line(line_clean):
                logger.debug(f"Skipping item line (separator): '{line_clean[:60]}'")
                continue

            # Detect metadata section markers
            if re.search(r"server\s*:|check\s*#|ordered\s*:", line_clean, re.IGNORECASE):
                in_metadata_section = True
                logger.debug(f"Entering metadata section: '{line_clean[:60]}'")
                # Skip the metadata line itself
                continue

            # If we're in metadata section, skip until we see an item indicator
            if in_metadata_section:
                # Check if this looks like an item (has price or item-like pattern)
                has_price = re.search(r"\$\d+\.\d{2}", line_clean)
                has_item_pattern = re.search(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+-\s+[A-Z])?", line_clean)

                if has_price or has_item_pattern:
                    # We've found an item, exit metadata section
                    in_metadata_section = False
                    logger.debug(f"Exiting metadata section, found item: '{line_clean[:60]}'")
                else:
                    # Still in metadata section, skip this line
                    # This catches customer names, server names, etc. that appear after "Check #"
                    logger.debug(f"Skipping item line (in metadata section): '{line_clean[:60]}'")
                    continue

            # Skip "Served by" lines
            if re.search(r"served\s+by", line_lower):
                logger.debug(f"Skipping item line (served by): '{line_clean[:60]}'")
                continue

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

            # Extract item name and price
            item_name = None
            item_price = None

            # Pattern 1: item name followed by price (e.g., "Classic - Mixed Plate $12.50")
            item_match = re.match(r"^(.+?)\s+\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*$", line_clean)
            if item_match:
                item_name = item_match.group(1).strip()
                price_str = item_match.group(2)
                # Verify it's a reasonable price (not a phone number or date)
                try:
                    price_val = Decimal(price_str.replace(",", ""))
                    if 0.01 <= price_val <= 1000:  # Reasonable price range
                        item_price = price_val
                except (InvalidOperation, ValueError):
                    pass
            else:
                # Pattern 2: Try without dollar sign
                item_match = re.match(r"^(.+?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*$", line_clean)
                if item_match:
                    item_name = item_match.group(1).strip()
                    price_str = item_match.group(2)
                    try:
                        price_val = Decimal(price_str.replace(",", ""))
                        if 0.01 <= price_val <= 1000:
                            item_price = price_val
                    except (InvalidOperation, ValueError):
                        pass
                else:
                    # Pattern 3: Item without explicit price (might be $0.00 or free item)
                    # Check if line looks like an item (has dashes, multiple words, etc.)
                    if re.search(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+-\s+[A-Z])?", line_clean):
                        item_name = line_clean
                        item_price = Decimal("0.00")  # Default to $0.00 for items without prices

            if not item_name:
                continue

            # Clean up item name
            item_name = re.sub(r"^\d+\s*", "", item_name)  # Remove leading numbers
            item_name = re.sub(r"^x\s+", "", item_name, flags=re.IGNORECASE)  # Remove leading "x" prefix
            item_name = re.sub(r"\s+", " ", item_name).strip()  # Normalize whitespace

            # Skip if matches restaurant name (exact or partial match)
            if restaurant_name:
                restaurant_lower = restaurant_name.lower()
                item_lower = item_name.lower()
                # Check for exact match or if restaurant name is contained in item
                if item_lower == restaurant_lower or restaurant_lower in item_lower or item_lower in restaurant_lower:
                    logger.debug(
                        f"Skipping item line (matches restaurant name): '{item_name}' (restaurant: '{restaurant_name}')"
                    )
                    continue

                # Check if line contains restaurant name words (e.g., "HAWAIIAN BROS" or "ISLAND GRILL")
                restaurant_words = set(re.findall(r"\b\w+\b", restaurant_lower))
                item_words = set(re.findall(r"\b\w+\b", item_lower))
                # If more than 50% of words match, likely the restaurant name
                if restaurant_words and len(item_words & restaurant_words) >= min(2, len(restaurant_words)):
                    logger.debug(f"Skipping item line (contains restaurant name words): '{item_name}'")
                    continue

            # Skip lines that are all caps and short (likely headers or restaurant names)
            # But only if they're very short (≤3 words, <30 chars) and don't have prices
            if line_clean.isupper() and len(line_clean.split()) <= 3 and len(line_clean) < 30:
                # Check if it has a price - if so, it might be an item
                if not re.search(r"\$\d+\.\d{2}", line_clean):
                    logger.debug(f"Skipping item line (all caps, short, likely header): '{line_clean}'")
                    continue

            # Skip single capitalized words that look like names (no price, no item pattern)
            # This catches customer names like "Morgan" that appear after "Check #"
            if (
                len(line_clean.split()) == 1
                and line_clean[0].isupper()
                and line_clean.isalpha()
                and not re.search(r"\$\d+\.\d{2}", line_clean)
                and not re.search(r"^[A-Z][a-z]+\s+-\s+", line_clean)
            ):  # Not an item pattern like "Classic - Mixed Plate"
                logger.debug(f"Skipping item line (looks like a name): '{line_clean}'")
                continue

            # Must have at least 3 characters and some letters
            if len(item_name) >= 3 and re.search(r"[a-zA-Z]{2,}", item_name):
                if item_name.lower() not in ["item", "description", "qty", "quantity", "price", "served", "by"]:
                    items.append({"name": item_name, "price": item_price})
                    logger.debug(f"Extracted item: '{item_name}' ${item_price} from line '{line_clean[:60]}'")

        logger.debug(f"Extracted {len(items)} items total")
        return items[:10]  # Limit to 10 items

    def _extract_amounts_from_totals_section(self, section_lines: list[str]) -> dict[str, Decimal | None]:
        """Extract amounts from totals section.

        Args:
            section_lines: Lines from totals section

        Returns:
            Dictionary with 'subtotal', 'tax', 'tip', 'total', 'amount' keys
        """
        amounts: dict[str, Decimal | None] = {
            "subtotal": None,
            "tax": None,
            "tip": None,
            "total": None,
            "amount": None,
        }

        # Labels for each amount type
        labels = {
            "subtotal": ["subtotal", "sub total", "sub-total"],
            "tax": ["tax", "sales tax", "gst", "vat", "hst"],
            "tip": ["tip", "gratuity", "service"],
            "total": ["total", "grand total", "final total"],
            "amount": ["amount paid", "amount", "paid", "charge", "due", "balance"],
        }

        for line in section_lines:
            line_lower = line.lower()
            # Check for table format
            if "|" in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2:
                    label = parts[0].lower()
                    amount_str = parts[-1].strip()  # Last column is usually the amount
                    # Extract amount from string
                    amount_match = re.search(r"\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", amount_str)
                    if amount_match:
                        try:
                            amount = Decimal(amount_match.group(1).replace(",", ""))
                            # Match label to amount type
                            for amount_type, keywords in labels.items():
                                if any(keyword in label for keyword in keywords):
                                    current = amounts[amount_type]
                                    if current is None or amount > current:
                                        amounts[amount_type] = amount
                                    break
                        except (InvalidOperation, ValueError):
                            continue
            else:
                # Line format: "Subtotal $72.30" or "Subtotal: $72.30"
                for amount_type, keywords in labels.items():
                    for keyword in keywords:
                        pattern = rf"{keyword}\s*:?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
                        match = re.search(pattern, line_lower, re.IGNORECASE)
                        if match:
                            try:
                                amount = Decimal(match.group(1).replace(",", ""))
                                current = amounts[amount_type]
                                if current is None or amount > current:
                                    amounts[amount_type] = amount
                            except (InvalidOperation, ValueError):
                                continue

        return amounts

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

        # More flexible amount patterns to handle OCR errors and fragmentation
        # Common OCR mistakes: O instead of 0, S instead of 5, I instead of 1
        # Also handle split amounts like "$3" and "29" → "$3.29"
        # And handle spaces instead of decimal points: "870 .16" → "$70.16"
        amount_patterns = [
            r"\$?\s*(\d{1,3}(?:[,\s]\d{3})*(?:[.,]\d{2})?)",  # Standard: $25.50, 25.50
            r"\$?\s*(\d+[.,]\d{2})",  # Simple: 25.50 or 25,50
            r"(\d{1,3}(?:[,\s]\d{3})*[.,]\d{2})",  # Without $: 25.50
            r"(\d+[.,]\d{1,2})",  # Allow 1 or 2 decimal places
            r"(\d{2,3})\s+[.,]\s*(\d{2})",  # OCR error: "870 .16" or "75 .95"
        ]

        # Look for labeled amounts (TOTAL, TAX, TIP, SUBTOTAL)
        labels = {
            "total": ["total", "amount due", "grand total", "final total", "balance", "amount", "charge"],
            "tax": ["tax", "sales tax", "gst", "vat", "hst"],
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
                keyword_with_amount_pattern = (
                    rf"^\s*{keyword}\s*[:=]?\s*\$?\s*(\d{1,3}(?:[,\s]\d{3})*(?:[.,]\d{2})?)\s*$"
                )
                for idx, line in enumerate(lines):
                    line_stripped = line.strip()
                    line_lower = line_stripped.lower()

                    # First, check for same-line pattern: "Keyword: $amount" or "Keyword $amount"
                    same_line_match = re.match(keyword_with_amount_pattern, line_lower, re.IGNORECASE)
                    if same_line_match:
                        logger.debug(f"Found keyword '{keyword}' with amount on same line {idx}: '{line_stripped}'")
                        try:
                            amount_str = same_line_match.group(1).replace(",", "").replace(" ", "").replace(",", ".")
                            if "," in amount_str and "." not in amount_str:
                                amount_str = amount_str.replace(",", ".")
                            amount = Decimal(amount_str)
                            logger.debug(f"    Parsed amount: {amount}")

                            # Filter out phone numbers
                            if amount >= 100 and amount < 1000 and "." not in same_line_match.group(0):
                                logger.debug("    Skipped (phone number filter)")
                                continue

                            # Filter reasonable amounts (including $0.00 for gratuity/tip)
                            if 0.00 <= amount <= 10000:
                                # Pattern 2 (same-line matching with keyword first) is more accurate than Pattern 1,
                                # so always override Pattern 1's value when we find a labeled amount
                                amounts[amount_type] = amount
                                logger.debug(
                                    f"Found labeled {amount_type}: ${amount} "
                                    f"(keyword '{keyword}' with amount on same line {idx}='{line_stripped}')"
                                )
                                break  # Found amount for this keyword, move to next keyword
                            else:
                                logger.debug("    Skipped (outside range)")
                        except (InvalidOperation, ValueError) as e:
                            logger.debug(f"    Error parsing amount: {e}")
                            continue

                    # Second, check for keyword-only line, then check next line for amount
                    if re.match(keyword_pattern, line_lower, re.IGNORECASE):
                        logger.debug(f"Found keyword '{keyword}' on line {idx}: '{line_stripped}'")
                        # Found keyword-only line, check next line for amount
                        if idx + 1 < len(lines):
                            next_line = lines[idx + 1]
                            logger.debug(f"  Checking next line {idx + 1} for amount: '{next_line.strip()}'")
                            # Try all amount patterns on the next line
                            for pattern_idx, pattern_check in enumerate(amount_patterns):
                                amount_match = re.search(pattern_check, next_line)
                                if amount_match:
                                    logger.debug(f"    Pattern {pattern_idx} matched: {amount_match.group(0)}")
                                    try:
                                        if len(amount_match.groups()) >= 2 and amount_match.group(2) is not None:
                                            # Special pattern with separate dollars and cents (like "870 .16")
                                            dollars = amount_match.group(1)
                                            cents = amount_match.group(2)
                                            amount_str = f"{dollars}.{cents}"
                                        else:
                                            # Regular pattern
                                            amount_str = (
                                                amount_match.group(1)
                                                .replace(",", "")
                                                .replace(" ", "")
                                                .replace(",", ".")
                                            )
                                            if "," in amount_str and "." not in amount_str:
                                                amount_str = amount_str.replace(",", ".")
                                        amount = Decimal(amount_str)
                                        logger.debug(f"    Parsed amount: {amount}")

                                        # Filter out phone numbers
                                        if amount >= 100 and amount < 1000 and "." not in amount_match.group(0):
                                            logger.debug("    Skipped (phone number filter)")
                                            continue

                                        # Filter reasonable amounts (including $0.00 for gratuity/tip)
                                        if 0.00 <= amount <= 10000:
                                            # Pattern 2 (next-line matching) is more accurate than Pattern 1,
                                            # so always override Pattern 1's value when we find a labeled amount
                                            amounts[amount_type] = amount
                                            logger.debug(
                                                f"Found labeled {amount_type}: ${amount} "
                                                f"(keyword '{keyword}' on line {idx}='{line_stripped}', "
                                                f"amount on line {idx + 1}='{next_line.strip()}')"
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

            # Special handling for fragmented amounts (like "$3" on one line, "29" on next)
            if idx < len(lines) - 1:
                current_line = line.strip()
                next_line = lines[idx + 1].strip()

                # Pattern 1: "$3" followed by "29" (fragmented price)
                dollars_match = re.search(r"^\$?(\d+)(?:\.\d{2})?$", current_line)
                cents_match = re.search(r"^(\d{2})$", next_line)

                if dollars_match and cents_match and not current_line.endswith(".00"):
                    try:
                        dollars = int(dollars_match.group(1))
                        cents = int(cents_match.group(1))
                        if dollars <= 1000 and cents <= 99:  # Reasonable ranges
                            amount = Decimal(f"{dollars}.{cents:02d}")
                            all_amounts.append((amount, idx, f"{current_line} {next_line}"))
                            logger.debug(
                                f"    -> Extracted fragmented amount: ${amount} from '{current_line} {next_line}'"
                            )
                            continue  # Skip regular pattern matching for this line
                    except (InvalidOperation, ValueError):
                        pass

                # Pattern 2: "870" followed by ".16" (OCR error with space instead of decimal)
                if re.match(r"^\d{3}$", current_line) and re.match(r"^\.\d{2}$", next_line):
                    try:
                        dollars = int(current_line)
                        cents_str = next_line[1:]  # Remove the "."
                        cents = int(cents_str)
                        amount = Decimal(f"{dollars}.{cents:02d}")
                        all_amounts.append((amount, idx, f"{current_line}{next_line}"))
                        logger.debug(f"    -> Extracted OCR error amount: ${amount} from '{current_line}{next_line}'")
                        continue
                    except (InvalidOperation, ValueError):
                        pass

            for pattern_idx, pattern in enumerate(amount_patterns):
                matches_list = list(re.finditer(pattern, line))
                if matches_list:
                    logger.debug(
                        f"  Line {idx} (pattern {pattern_idx}): Found {len(matches_list)} matches in '{line[:80]}'"
                    )
                for match in matches_list:
                    try:
                        if len(match.groups()) >= 2 and match.group(2) is not None:
                            # Special pattern with separate dollars and cents (like "870 .16")
                            dollars = match.group(1)
                            cents = match.group(2)
                            amount_str = f"{dollars}.{cents}"
                        else:
                            # Regular pattern
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
            except (TypeError, ValueError, AttributeError) as e:
                logger.debug(f"Error calculating subtotal: {e}")
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

    def _parse_bank_statement(self, text: str, lines: list[str], receipt_data: Any) -> Any:
        """Parse bank statement data to extract transaction information.

        Args:
            text: Full text content
            lines: List of text lines

        Returns:
            ReceiptData object with parsed fields
        """
        receipt_data.raw_text = text

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
            r"(\d{1,2}[/-]\d{1,2}[/-]?\d{0,4})",  # MM/DD/YYYY or MM/DD/YY
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
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.debug(f"Unexpected error parsing date '{date_str}': {e}")
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
        # _extract_restaurant_name always returns a tuple, so return just the name
        return name_result[0]  # Return just the name for bank statements

    def _extract_transactions(self, lines: list[str]) -> list[dict[str, Any]]:
        """Extract transaction data from bank statement lines.

        Args:
            lines: List of text lines from bank statement

        Returns:
            List of transaction dictionaries with 'date', 'merchant', 'amount' keys
        """
        transactions: list[dict[str, Any]] = []
        date_pattern = r"(\d{1,2}[/-]\d{1,2}[/-]?\d{0,4})"
        amount_pattern = r"[-\(]?\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\)?\s*[DB]?"

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
            "burger",
            "taco",
            "bar",
            "pub",
            "food",
            "kitchen",
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

    def _is_separator_line(self, line: str) -> bool:
        """Check if a line is a separator (dashes, underscores, equals, etc.).

        Args:
            line: Text line to check

        Returns:
            True if line appears to be a separator
        """
        line_clean = line.strip()
        if not line_clean:
            return False

        # Check for separator patterns: mostly repeating characters
        # Examples: "———", "---", "===", "___", "— ISLAND GRILL —"
        # Count non-whitespace, non-alphanumeric characters
        non_alnum = sum(1 for c in line_clean if not c.isalpha() and not c.isspace())
        total_chars = len([c for c in line_clean if not c.isspace()])

        if total_chars == 0:
            return False

        # If >70% of characters are separator characters, it's likely a separator
        separator_ratio = non_alnum / total_chars if total_chars > 0 else 0
        if separator_ratio > 0.7:
            return True

        # Check for patterns like "— TEXT —" or "--- TEXT ---"
        if re.match(r"^[—\-=_·•|]+\s*[A-Za-z\s]*\s*[—\-=_·•|]+$", line_clean):
            return True

        return False

    def _to_proper_case(self, text: str) -> str:
        """Convert ALL CAPS text to Proper Case (Title Case).

        Args:
            text: Text to convert

        Returns:
            Text in proper case
        """
        if not text:
            return text

        # Check if text is all caps (excluding punctuation and spaces)
        letters = [c for c in text if c.isalpha()]
        if not letters:
            return text

        # If >80% of letters are uppercase, convert to title case
        uppercase_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        if uppercase_ratio > 0.8:
            # Use title() but handle special cases
            # Preserve common abbreviations and small words
            words = text.split()
            result_words = []
            for word in words:
                # Preserve all-caps abbreviations (2-4 chars) like "LLC", "INC", "USA"
                # But convert restaurant-related words like "BROS" to proper case
                restaurant_words = {
                    "bros",
                    "grill",
                    "cafe",
                    "diner",
                    "kitchen",
                    "pizza",
                    "bar",
                    "tavern",
                    "bistro",
                    "eatery",
                    "deli",
                }
                if word.isupper() and 2 <= len(word) <= 4 and word.isalpha():
                    # Convert restaurant words to proper case, preserve other abbreviations
                    if word.lower() in restaurant_words:
                        result_words.append(word.title())
                    else:
                        result_words.append(word)
                else:
                    # Convert to title case
                    result_words.append(word.title())
            return " ".join(result_words)

        return text

    def _find_section_boundaries(self, lines: list[str]) -> tuple[int, int]:
        """Find the start and end indices for the items section using separators.

        Args:
            lines: List of text lines

        Returns:
            Tuple of (start_idx, end_idx) for items section
        """
        # Find separator lines
        separator_indices: list[int] = []
        for idx, line in enumerate(lines):
            if self._is_separator_line(line):
                separator_indices.append(idx)

        logger.debug(f"Found {len(separator_indices)} separator lines at indices: {separator_indices}")

        # Items typically start after the first separator (after restaurant/order info)
        # and end before the last separator or totals section
        start_idx = 0
        end_idx = len(lines)

        if separator_indices:
            # Start after first separator (or use default if separator is too early)
            first_separator = separator_indices[0]
            start_idx = min(first_separator + 1, len(lines))
            # But don't start too early (skip email headers)
            start_idx = max(start_idx, min(5, len(lines)))

            # End before last separator or totals section
            if len(separator_indices) > 1:
                last_separator = separator_indices[-1]
                end_idx = max(last_separator, start_idx)
            else:
                # Only one separator, items end before totals (last 5-7 lines)
                end_idx = max(len(lines) - 7, start_idx)
        else:
            # No separators found, use conservative defaults
            start_idx = min(5, len(lines))
            end_idx = max(len(lines) - 7, start_idx)

        # Find totals section (look for "total", "tax", "tip", "subtotal")
        totals_keywords = ["total", "tax", "tip", "subtotal"]
        for idx in range(len(lines) - 1, max(start_idx, len(lines) - 10), -1):
            line_lower = lines[idx].lower()
            if any(keyword in line_lower for keyword in totals_keywords):
                end_idx = min(idx, end_idx)
                break

        logger.debug(f"Items section boundaries: start={start_idx}, end={end_idx} (out of {len(lines)} total lines)")

        return start_idx, end_idx

    def _calculate_confidence_scores(self, receipt_data: Any) -> dict[str, float]:
        """Calculate confidence scores for extracted fields.

        Args:
            receipt_data: Any object

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
