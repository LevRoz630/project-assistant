"""Security logging and monitoring utilities."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

# Configure security logger
security_logger = logging.getLogger("security")
security_logger.setLevel(logging.WARNING)

# Add handler if not already present
if not security_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - SECURITY - %(levelname)s - %(message)s"
        )
    )
    security_logger.addHandler(handler)


class SecurityEventType:
    """Security event type constants."""

    INJECTION_ATTEMPT = "injection_attempt"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    INPUT_VALIDATION_FAILED = "input_validation_failed"


def log_security_event(
    event_type: str,
    session_id: str | None,
    details: dict[str, Any],
) -> None:
    """
    Log a security event for monitoring and alerting.

    Args:
        event_type: Type of security event (use SecurityEventType constants)
        session_id: Session ID (will be truncated for privacy)
        details: Additional details about the event
    """
    truncated_session = session_id[:8] if session_id else "unknown"

    log_data = {
        "event_type": event_type,
        "session_id": truncated_session,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details,
    }

    security_logger.warning(
        f"SECURITY_EVENT: {event_type} | session={truncated_session} | details={details}"
    )

    return log_data


def safe_error_message(error: Exception, operation: str, include_details: bool = False) -> str:
    """
    Generate a safe error message that doesn't leak internal details.

    Args:
        error: The exception that occurred
        operation: A short description of the operation that failed
        include_details: If True, include generic error type (not full message)

    Returns:
        A safe error message suitable for client responses
    """
    # Log the full error for debugging
    error_id = str(uuid.uuid4())[:8]
    security_logger.info(
        f"ERROR_REF:{error_id} | operation={operation} | error={type(error).__name__}: {error}"
    )

    # Return a generic message with reference ID for support
    if include_details:
        return f"{operation} failed (ref: {error_id})"
    return f"{operation} failed. Please try again or contact support (ref: {error_id})"
