"""URL utility helpers."""

from urllib.parse import urlsplit, urlunsplit

_COMMON_COMPOUND_SUFFIXES = {
    "co.uk",
    "org.uk",
    "gov.uk",
    "ac.uk",
    "com.au",
    "net.au",
    "org.au",
    "co.nz",
    "com.br",
    "com.mx",
    "co.jp",
}


def canonicalize_website_for_storage(url: str | None) -> str | None:
    """Normalize a website URL for storage: strip query/fragment, lowercase host, path without trailing slash.

    Defaults to https if no scheme is present. Returns None for empty or invalid input.
    Used consistently by restaurants, merchants, and Google Places ingestion.
    """
    if not url or not isinstance(url, str):
        return None
    cleaned = (strip_url_query_params(url) or url).strip()
    if not cleaned:
        return None
    try:
        parts = urlsplit(cleaned)
        if not parts.netloc:
            return None
        scheme = parts.scheme.lower() if parts.scheme else "https"
        host = parts.netloc.lower()
        path = (parts.path or "/").rstrip("/") or "/"
        return urlunsplit((scheme, host, path, "", ""))
    except ValueError:
        return cleaned if cleaned else None


def get_favicon_host_candidates(url: str | None) -> list[str]:
    """Return a bounded list of host names to try for favicon resolution (canonical host plus www/apex alternate).

    Used so favicon logic can try both www and apex for the same logical site (e.g. chick-fil-a.com).
    Returns at most two unique hosts; empty list if url is invalid.
    """
    if not url or not isinstance(url, str):
        return []
    canonical = canonicalize_website_for_storage(url)
    if not canonical:
        return []
    try:
        parts = urlsplit(canonical)
        host = parts.netloc.lower()
        if not host or "." not in host:
            return []
        candidates = [host]
        if host.startswith("www."):
            apex = host[4:]
            if apex and apex not in candidates:
                candidates.append(apex)
        else:
            www_host = "www." + host
            if www_host not in candidates:
                candidates.append(www_host)
        return candidates[:2]
    except ValueError:
        return []


def normalize_website_for_comparison(url: str | None) -> str:
    """Normalize website URL for comparison (strip params, trailing slash, lowercase)."""
    if not url or not isinstance(url, str):
        return ""
    cleaned = strip_url_query_params(url) or url.strip()
    if not cleaned:
        return ""
    try:
        parts = urlsplit(cleaned)
        path = parts.path.rstrip("/") or "/"
        normalized = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))
        return normalized
    except ValueError:
        return cleaned.lower()


def validate_favicon_url(url: str | None) -> str | None:
    """Return the URL if it is a valid http/https favicon URL; otherwise None.

    Used for merchant favicon_url override. Empty or invalid input returns None.
    """
    if not url or not isinstance(url, str):
        return None
    cleaned = url.strip()
    if not cleaned:
        return None
    try:
        parts = urlsplit(cleaned)
        if not parts.netloc or parts.scheme not in ("http", "https"):
            return None
        return cleaned
    except ValueError:
        return None


def extract_comparable_website_host(url: str | None) -> str:
    """Return a comparable website host for merchant matching.

    Normalizes case and strips a leading ``www.`` so brand sites can match
    regardless of whether the stored URL uses apex or www form.
    """
    if not url or not isinstance(url, str):
        return ""

    canonical = canonicalize_website_for_storage(url)
    if not canonical:
        return ""

    try:
        host = urlsplit(canonical).netloc.lower().strip()
    except ValueError:
        return ""

    if host.startswith("www."):
        host = host[4:]
    return host


def extract_base_website_url(url: str | None) -> str:
    """Return a canonical base website URL using the apex host and root path.

    This is useful when a location-level page should prefill a brand-level website
    field. It keeps the canonical scheme, strips query/fragment state, removes a
    leading ``www.``, and resets the path to ``/``.
    """
    if not url or not isinstance(url, str):
        return ""

    canonical = canonicalize_website_for_storage(url)
    if not canonical:
        return ""

    try:
        parts = urlsplit(canonical)
        host = parts.netloc.lower().strip()
    except ValueError:
        return ""

    if not host:
        return ""
    host = _extract_apex_host(host)
    if not host:
        return ""

    return urlunsplit((parts.scheme.lower() or "https", host, "", "", ""))


def _extract_apex_host(host: str) -> str:
    """Return an apex host from a fully-qualified hostname.

    Keeps the registrable domain for common public suffix patterns and falls
    back to the last two labels for standard domains like ``restaurant.com``.
    """
    cleaned = host.strip().lower()
    if cleaned.startswith("www."):
        cleaned = cleaned[4:]

    labels = [label for label in cleaned.split(".") if label]
    if len(labels) <= 2:
        return ".".join(labels)

    suffix = ".".join(labels[-2:])
    if suffix in _COMMON_COMPOUND_SUFFIXES and len(labels) >= 3:
        return ".".join(labels[-3:])

    return ".".join(labels[-2:])


def strip_url_query_params(url: str | None) -> str | None:
    """Strip query params from a URL if present."""
    if not url or not isinstance(url, str):
        return None

    cleaned_url = url.strip()
    if not cleaned_url:
        return None

    try:
        parts = urlsplit(cleaned_url)
    except ValueError:
        return cleaned_url

    if not parts.query:
        return cleaned_url

    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", parts.fragment))
