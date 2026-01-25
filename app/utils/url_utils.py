"""URL utility helpers."""

from urllib.parse import urlsplit, urlunsplit


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
