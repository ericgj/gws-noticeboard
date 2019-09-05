from urllib.parse import urlparse, urlunparse


def standardized_url(url: str) -> str:
    parts = urlparse(url)
    return urlunparse(parts._replace(netloc=parts.netloc.lower()))
