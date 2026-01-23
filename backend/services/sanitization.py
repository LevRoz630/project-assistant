"""Sanitization utilities for prompt injection defense."""

import html
import re
import unicodedata


class PromptSanitizer:
    """Sanitize external data before injecting into LLM prompts."""

    # Patterns that may indicate prompt injection attempts
    DANGEROUS_PATTERNS = [
        # Original patterns - instruction override attempts
        r"ignore\s*(all\s*)?(previous|prior|above)\s*(instructions?|prompts?)",
        r"forget\s*(all\s*)?(previous|prior|above)",
        r"you\s+are\s+now\s+(a|an|in)",
        r"new\s+(instructions?|rules?|role)",
        r"system\s*prompt",
        r"override\s*(instructions?|rules?)",
        r"disregard\s*(previous|prior|above)",
        r"act\s+as\s+(if\s+)?(a|an|you)",
        r"pretend\s+(to\s+be|you\s+are)",
        r"jailbreak",
        r"DAN\s+mode",
        r"\bDAN\b",
        # Role switching in code blocks
        r"```\s*(system|assistant|user)",
        # Common instruction markers
        r"\[INST\]|\[/INST\]",
        # Model-specific tokens
        r"<\|.*?\|>",
        # Role labels
        r"(^|\s)(human|assistant|system)\s*:",
        # Markdown role markers
        r"###\s*(instruction|response|system)",
        # Identity manipulation
        r"as\s+an?\s+(ai|language\s+model|chatbot|assistant)",
        # Imperative commands to AI
        r"you\s+(must|will|shall|should)\s+(now|always|never)",
        # Context escape attempts
        r"(end|exit|escape)\s*(context|prompt|instruction)",
        r"===+\s*(end|system|new)",
    ]

    # Compiled patterns for efficiency
    _compiled_patterns: list[re.Pattern] | None = None

    @classmethod
    def _get_patterns(cls) -> list[re.Pattern]:
        """Get compiled regex patterns (lazy initialization)."""
        if cls._compiled_patterns is None:
            cls._compiled_patterns = [
                re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                for pattern in cls.DANGEROUS_PATTERNS
            ]
        return cls._compiled_patterns

    @classmethod
    def normalize_unicode(cls, text: str) -> str:
        """
        Normalize unicode to prevent obfuscation attacks.

        Converts various unicode representations to their canonical form,
        preventing attackers from using lookalike characters to bypass filters.
        """
        # NFKC normalization converts compatibility characters to their canonical form
        # e.g., "ｉｇｎｏｒｅ" (fullwidth) -> "ignore" (ASCII)
        return unicodedata.normalize("NFKC", text)

    @classmethod
    def contains_injection_attempt(cls, text: str) -> bool:
        """Check if text contains potential prompt injection patterns."""
        # Normalize unicode first to catch obfuscation attempts
        normalized = cls.normalize_unicode(text)
        for pattern in cls._get_patterns():
            if pattern.search(normalized):
                return True
        return False

    @classmethod
    def sanitize(
        cls,
        text: str,
        max_length: int = 500,
        escape_html: bool = True,
        filter_injections: bool = True,
    ) -> str:
        """
        Sanitize external text before including in prompts.

        Args:
            text: The text to sanitize
            max_length: Maximum length to allow (truncates if longer)
            escape_html: Whether to escape HTML special characters
            filter_injections: Whether to check for injection patterns

        Returns:
            Sanitized text safe for prompt inclusion
        """
        if not text:
            return ""

        # Normalize unicode first to prevent obfuscation
        result = cls.normalize_unicode(text)

        # Truncate to prevent DOS/context overflow
        result = result[:max_length]

        # Normalize whitespace (collapse multiple spaces/newlines)
        result = " ".join(result.split())

        # Escape HTML entities to prevent format breaking
        if escape_html:
            result = html.escape(result)

        # Check for injection patterns
        if filter_injections and cls.contains_injection_attempt(result):
            return "[Content filtered for security]"

        return result

    @classmethod
    def sanitize_dict(cls, data: dict, max_length: int = 500) -> dict:
        """
        Sanitize all string values in a dictionary.

        Args:
            data: Dictionary with potentially unsafe values
            max_length: Maximum length for string values

        Returns:
            Dictionary with sanitized string values
        """
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = cls.sanitize(value, max_length=max_length)
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value, max_length=max_length)
            elif isinstance(value, list):
                sanitized[key] = [
                    cls.sanitize(v, max_length=max_length) if isinstance(v, str) else v
                    for v in value
                ]
            else:
                sanitized[key] = value
        return sanitized


def sanitize_email_content(
    sender: str,
    subject: str,
    preview: str,
) -> tuple[str, str, str]:
    """
    Sanitize email content for prompt inclusion.

    Returns:
        Tuple of (sanitized_sender, sanitized_subject, sanitized_preview)
    """
    return (
        PromptSanitizer.sanitize(sender, max_length=100),
        PromptSanitizer.sanitize(subject, max_length=200),
        PromptSanitizer.sanitize(preview, max_length=300),
    )


def sanitize_task_content(title: str, body: str | None = None) -> tuple[str, str]:
    """
    Sanitize task content for prompt inclusion.

    Returns:
        Tuple of (sanitized_title, sanitized_body)
    """
    return (
        PromptSanitizer.sanitize(title, max_length=200),
        PromptSanitizer.sanitize(body or "", max_length=500),
    )


def sanitize_calendar_content(
    subject: str,
    location: str | None = None,
    organizer: str | None = None,
) -> tuple[str, str, str]:
    """
    Sanitize calendar event content for prompt inclusion.

    Returns:
        Tuple of (sanitized_subject, sanitized_location, sanitized_organizer)
    """
    return (
        PromptSanitizer.sanitize(subject, max_length=200),
        PromptSanitizer.sanitize(location or "", max_length=100),
        PromptSanitizer.sanitize(organizer or "", max_length=100),
    )


def sanitize_note_content(content: str, source: str) -> tuple[str, str]:
    """
    Sanitize note/RAG content for prompt inclusion.

    Returns:
        Tuple of (sanitized_content, sanitized_source)
    """
    return (
        PromptSanitizer.sanitize(content, max_length=1000),
        PromptSanitizer.sanitize(source, max_length=200),
    )
