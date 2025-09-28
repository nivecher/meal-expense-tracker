"""
Favicon Service
Handles fetching and caching restaurant favicons from various sources
Following TIGER principles: Safety, Performance, Developer Experience
"""

import base64
import logging
import re
import time
from io import BytesIO
from typing import Any, Dict, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from flask import current_app
from PIL import Image

# Set up logging
logger = logging.getLogger(__name__)


class FaviconService:
    """Service for fetching and caching restaurant favicons"""

    def __init__(self):
        """Initialize favicon service with cache and configuration"""
        self.cache = {}  # In-memory cache for favicons
        self.cache_duration = 86400  # 24 hours in seconds
        self.timeout = 5  # Request timeout in seconds
        self.max_file_size = 1024 * 1024  # 1MB max favicon size

        # Favicon source URLs in order of preference
        self.favicon_sources = [
            lambda domain: f"https://{domain}/favicon.ico",
            lambda domain: f"https://www.google.com/s2/favicons?domain={domain}&sz=32",
            lambda domain: f"https://icons.duckduckgo.com/ip3/{domain}.ico",
            lambda domain: f"https://www.getfavicon.org/?url=https://{domain}",
        ]

    def get_favicon_url(self, website_url: str) -> Optional[str]:
        """
        Get favicon URL for a restaurant website

        Args:
            website_url: The restaurant's website URL

        Returns:
            Base64 encoded favicon data URL or None if not found
        """
        if not website_url or not isinstance(website_url, str):
            logger.warning("Invalid website URL provided")
            return None

        domain = self._extract_domain(website_url)
        if not domain:
            logger.warning(f"Could not extract domain from: {website_url}")
            return None

        # Check cache first
        cache_key = f"favicon_{domain}"
        cached_result = self._get_cached_favicon(cache_key)
        if cached_result is not None:
            return cached_result

        # Try to fetch favicon
        favicon_data = self._fetch_favicon(domain, website_url)

        # Cache the result (even if None)
        self._cache_favicon(cache_key, favicon_data)

        return favicon_data

    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract clean domain from URL"""
        try:
            # Handle URLs without protocol
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"

            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove www prefix
            if domain.startswith("www."):
                domain = domain[4:]

            return domain if domain else None

        except Exception as error:
            logger.error(f"Error extracting domain from {url}: {error}")
            return None

    def _get_cached_favicon(self, cache_key: str) -> Optional[str]:
        """Get favicon from cache if not expired"""
        if cache_key not in self.cache:
            return None

        cached_data = self.cache[cache_key]
        timestamp = cached_data.get("timestamp", 0)

        # Check if cache is expired
        if time.time() - timestamp > self.cache_duration:
            del self.cache[cache_key]
            return None

        return cached_data.get("data")

    def _cache_favicon(self, cache_key: str, data: Optional[str]) -> None:
        """Cache favicon data with timestamp"""
        self.cache[cache_key] = {
            "data": data,
            "timestamp": time.time(),
        }

        # Enforce cache size limit (safety)
        if len(self.cache) > 1000:
            # Remove oldest entries
            oldest_keys = sorted(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])[:100]
            for key in oldest_keys:
                del self.cache[key]

    def _fetch_favicon(self, domain: str, website_url: str) -> Optional[str]:
        """
        Fetch favicon from various sources

        Args:
            domain: Clean domain name
            website_url: Original website URL for HTML parsing

        Returns:
            Base64 encoded favicon data URL or None
        """
        # First try to find favicon from website's HTML
        html_favicon = self._get_favicon_from_html(website_url)
        if html_favicon:
            return html_favicon

        # Try each favicon source
        for source_func in self.favicon_sources:
            try:
                favicon_url = source_func(domain)
                favicon_data = self._download_favicon(favicon_url)
                if favicon_data:
                    return favicon_data

            except Exception as error:
                logger.warning(f"Error fetching favicon from source: {error}")
                continue

        logger.info(f"No favicon found for domain: {domain}")
        return None

    def _get_favicon_from_html(self, website_url: str) -> Optional[str]:
        """Parse website HTML to find favicon links"""
        try:
            response = requests.get(
                website_url,
                timeout=self.timeout,
                headers={"User-Agent": "Mozilla/5.0 (compatible; FaviconBot/1.0)"},
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Look for various favicon link tags
            favicon_selectors = [
                'link[rel="icon"]',
                'link[rel="shortcut icon"]',
                'link[rel="apple-touch-icon"]',
                'link[rel="apple-touch-icon-precomposed"]',
            ]

            for selector in favicon_selectors:
                favicon_links = soup.select(selector)
                for link in favicon_links:
                    href = link.get("href")
                    if href:
                        # Convert relative URL to absolute
                        favicon_url = urljoin(website_url, href)
                        favicon_data = self._download_favicon(favicon_url)
                        if favicon_data:
                            return favicon_data

        except Exception as error:
            logger.warning(f"Error parsing HTML for favicon: {error}")

        return None

    def _download_favicon(self, favicon_url: str) -> Optional[str]:
        """
        Download and convert favicon to base64 data URL

        Args:
            favicon_url: URL of the favicon to download

        Returns:
            Base64 encoded data URL or None
        """
        try:
            response = requests.get(
                favicon_url,
                timeout=self.timeout,
                headers={"User-Agent": "Mozilla/5.0 (compatible; FaviconBot/1.0)"},
                stream=True,
            )
            response.raise_for_status()

            # Check content length (safety)
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > self.max_file_size:
                logger.warning(f"Favicon too large: {content_length} bytes")
                return None

            # Read content with size limit
            content = BytesIO()
            size = 0
            for chunk in response.iter_content(chunk_size=8192):
                size += len(chunk)
                if size > self.max_file_size:
                    logger.warning("Favicon download exceeded size limit")
                    return None
                content.write(chunk)

            favicon_bytes = content.getvalue()

            # Validate and potentially resize image
            processed_favicon = self._process_favicon_image(favicon_bytes)
            if not processed_favicon:
                return None

            # Determine content type
            content_type = response.headers.get("content-type", "image/x-icon")
            if not content_type.startswith("image/"):
                content_type = "image/x-icon"

            # Convert to base64 data URL
            base64_data = base64.b64encode(processed_favicon).decode("utf-8")
            return f"data:{content_type};base64,{base64_data}"

        except Exception as error:
            logger.warning(f"Error downloading favicon from {favicon_url}: {error}")
            return None

    def _process_favicon_image(self, image_bytes: bytes) -> Optional[bytes]:
        """
        Process and validate favicon image

        Args:
            image_bytes: Raw image bytes

        Returns:
            Processed image bytes or None if invalid
        """
        try:
            # Try to open and validate the image
            with Image.open(BytesIO(image_bytes)) as img:
                # Convert to standard format if needed
                if img.format not in ["ICO", "PNG", "JPEG", "GIF"]:
                    # Convert to PNG
                    output = BytesIO()
                    img.save(output, format="PNG")
                    return output.getvalue()
                else:
                    return image_bytes

        except Exception as error:
            logger.warning(f"Error processing favicon image: {error}")
            return None

    def clear_cache(self) -> None:
        """Clear favicon cache"""
        self.cache.clear()
        logger.info("Favicon cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self.cache),
            "cache_duration_hours": self.cache_duration / 3600,
            "max_file_size_mb": self.max_file_size / (1024 * 1024),
        }


# Global service instance
favicon_service = FaviconService()
