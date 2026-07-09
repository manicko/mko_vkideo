"""URL sanitization utilities for secure logging."""

from urllib.parse import urlparse, urlunparse

# Authentication-related query parameters to strip from logged URLs
AUTH_PARAMS = frozenset([
    "token",
    "access_token",
    "auth",
    "auth_token",
    "session",
    "session_id",
    "sid",
    "key",
    "signature",
    "sig",
    "expire",
    "expires",
    "expires_in",
    "timestamp",
    "nonce",
    "hash",
    "hmac",
    "secret",
])


def _strip_auth_params(url: str) -> str:
    """
    Remove authentication-related query parameters from URL for safe logging.

    Strips sensitive query parameters like tokens, keys, and signatures
    while preserving the base URL structure.

    Args:
        url: The original URL potentially containing auth parameters.

    Returns:
        URL with authentication parameters removed.
    """
    if not url or "?" not in url:
        return url

    try:
        parsed = urlparse(url)
        query_parts = []

        for param in parsed.query.split("&"):
            if not param:
                continue
            param_name = param.split("=")[0].lower()
            # Keep parameters that are not auth-related
            if param_name not in AUTH_PARAMS:
                query_parts.append(param)

        # Reconstruct URL without auth parameters
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            "&".join(query_parts) if query_parts else "",
            parsed.fragment,
        ))
    except Exception:
        # If parsing fails, return original URL
        return url
