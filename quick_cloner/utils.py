from urllib.parse import urlparse, urlunparse

MASK = "***"

def mask_pat(text: str, pat: str) -> str:
    if not pat:
        return text
    return text.replace(pat, MASK)

def embed_pat_in_url(url: str, username: str, pat: str) -> str:
    """Embed PAT credentials into an https:// URL safely."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")

    if parsed.port:
        netloc = f"{username}:{pat}@{parsed.hostname}:{parsed.port}"
    else:
        netloc = f"{username}:{pat}@{parsed.hostname}"

    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
