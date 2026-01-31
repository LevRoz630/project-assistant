"""Web page fetching and content extraction service."""

import ipaddress
import re
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from ..config import get_settings
from .sanitization import PromptSanitizer

settings = get_settings()

# Constants
FETCH_TIMEOUT = 15  # seconds
MAX_CONTENT_LENGTH = 50000  # characters
USER_AGENT = "Mozilla/5.0 (compatible; PersonalAIAssistant/1.0)"

# Domains/patterns to block for security/privacy
BLOCKED_DOMAIN_PATTERNS = [
    "localhost",
    "internal",
    "intranet",
    "corp",
    "local",
    ".internal",
    ".local",
    ".localhost",
]

# Private/reserved IP ranges that should never be fetched (SSRF protection)
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),        # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),     # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),    # Private Class C
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local
    ipaddress.ip_network("224.0.0.0/4"),       # Multicast
    ipaddress.ip_network("240.0.0.0/4"),       # Reserved
    ipaddress.ip_network("0.0.0.0/8"),         # Current network
    ipaddress.ip_network("100.64.0.0/10"),     # Shared address space (CGN)
    ipaddress.ip_network("198.18.0.0/15"),     # Benchmark testing
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 private
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]


class WebFetchError(Exception):
    """Error fetching web content."""

    pass


def _is_ip_blocked(ip_str: str) -> bool:
    """Check if an IP address falls within blocked ranges."""
    try:
        ip = ipaddress.ip_address(ip_str)
        for network in BLOCKED_IP_NETWORKS:
            if ip in network:
                return True
        return False
    except ValueError:
        # Invalid IP address format
        return True  # Block invalid IPs by default


def _is_hostname_blocked(hostname: str) -> bool:
    """Check if a hostname matches blocked patterns."""
    hostname_lower = hostname.lower()

    # Check against blocked patterns
    for pattern in BLOCKED_DOMAIN_PATTERNS:
        if pattern.startswith("."):
            # Suffix match (e.g., ".local" matches "foo.local")
            if hostname_lower.endswith(pattern) or hostname_lower == pattern[1:]:
                return True
        else:
            # Substring match
            if pattern in hostname_lower:
                return True

    # Block raw IP addresses that look like private IPs
    try:
        if _is_ip_blocked(hostname):
            return True
    except Exception:
        pass

    return False


def _resolve_and_check_ip(hostname: str) -> bool:
    """Resolve hostname to IP and verify it's not in blocked ranges."""
    try:
        # Resolve hostname to IP addresses
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)

        for family, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            if _is_ip_blocked(ip_str):
                return False

        return True
    except socket.gaierror:
        # DNS resolution failed - could be invalid hostname
        return False
    except Exception:
        return False


def _is_valid_url(url: str) -> tuple[bool, str]:
    """Check if URL is valid and safe to fetch.

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        parsed = urlparse(url)

        # Must have scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format"

        # Must be http or https
        if parsed.scheme not in ("http", "https"):
            return False, "Only HTTP and HTTPS URLs are allowed"

        # Check hostname against blocked patterns
        hostname = parsed.hostname or ""
        if not hostname:
            return False, "No hostname in URL"

        if _is_hostname_blocked(hostname):
            return False, "Blocked hostname"

        # Resolve DNS and check resolved IP against blocked ranges (SSRF protection)
        if not _resolve_and_check_ip(hostname):
            return False, "URL resolves to blocked IP range"

        return True, ""
    except Exception as e:
        return False, f"URL validation error: {e}"


def _extract_text_from_html(html: str, max_length: int = MAX_CONTENT_LENGTH) -> str:
    """
    Extract readable text content from HTML.

    Args:
        html: Raw HTML content
        max_length: Maximum length of extracted text

    Returns:
        Cleaned text content
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
        element.decompose()

    # Get text
    text = soup.get_text(separator="\n", strip=True)

    # Clean up whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)

    # Remove excessive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Truncate if needed
    if len(text) > max_length:
        text = text[:max_length] + "\n\n[Content truncated...]"

    return text


async def fetch_url(url: str) -> dict:
    """
    Fetch and extract text content from a URL.

    Args:
        url: The URL to fetch

    Returns:
        Dict with 'url', 'title', 'content', and 'success' keys
    """
    is_valid, error_msg = _is_valid_url(url)
    if not is_valid:
        return {
            "url": url,
            "title": "",
            "content": f"[Blocked: {error_msg}]",
            "success": False,
        }

    try:
        async with httpx.AsyncClient(
            timeout=FETCH_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                return {
                    "url": url,
                    "title": "",
                    "content": f"[Unsupported content type: {content_type}]",
                    "success": False,
                }

            html = response.text
            text = _extract_text_from_html(html)

            # Extract title
            soup = BeautifulSoup(html, "html.parser")
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""

            # Sanitize the content
            sanitized_content = PromptSanitizer.sanitize(
                text, max_length=MAX_CONTENT_LENGTH, filter_injections=True
            )

            return {
                "url": str(response.url),  # May differ from input if redirected
                "title": PromptSanitizer.sanitize(title, max_length=200),
                "content": sanitized_content,
                "success": True,
            }

    except httpx.TimeoutException:
        return {
            "url": url,
            "title": "",
            "content": "[Request timed out]",
            "success": False,
        }
    except httpx.HTTPStatusError as e:
        return {
            "url": url,
            "title": "",
            "content": f"[HTTP error: {e.response.status_code}]",
            "success": False,
        }
    except Exception as e:
        return {
            "url": url,
            "title": "",
            "content": f"[Error fetching URL: {e!s}]",
            "success": False,
        }


async def fetch_urls(urls: list[str], max_urls: int = 3) -> str:
    """
    Fetch multiple URLs and format results for LLM context.

    Args:
        urls: List of URLs to fetch
        max_urls: Maximum number of URLs to fetch

    Returns:
        Formatted string with all fetched content
    """
    results = []

    for url in urls[:max_urls]:
        result = await fetch_url(url)
        if result["success"]:
            title = result["title"] or "Untitled"
            content = result["content"]
            results.append(f"### {title}\nSource: {result['url']}\n\n{content}")
        else:
            results.append(f"### Failed to fetch: {url}\n{result['content']}")

    return "\n\n---\n\n".join(results) if results else ""
