"""Web page fetching and content extraction service."""

import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from config import get_settings
from services.sanitization import PromptSanitizer

settings = get_settings()

# Constants
FETCH_TIMEOUT = 15  # seconds
MAX_CONTENT_LENGTH = 50000  # characters
USER_AGENT = "Mozilla/5.0 (compatible; PersonalAIAssistant/1.0)"

# Domains to block for security/privacy
BLOCKED_DOMAINS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "internal",
    "intranet",
]


class WebFetchError(Exception):
    """Error fetching web content."""

    pass


def _is_valid_url(url: str) -> bool:
    """Check if URL is valid and safe to fetch."""
    try:
        parsed = urlparse(url)

        # Must have scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            return False

        # Must be http or https
        if parsed.scheme not in ("http", "https"):
            return False

        # Check blocked domains
        hostname = parsed.hostname or ""
        for blocked in BLOCKED_DOMAINS:
            if blocked in hostname.lower():
                return False

        return True
    except Exception:
        return False


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
    if not _is_valid_url(url):
        return {
            "url": url,
            "title": "",
            "content": "[Invalid or blocked URL]",
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
