"""Security logging and monitoring utilities."""

import logging
from datetime import datetime
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
        "timestamp": datetime.now(datetime.timezone.utc).isoformat(),
        "details": details,
    }

    security_logger.warning(
        f"SECURITY_EVENT: {event_type} | session={truncated_session} | details={details}"
    )

    return log_data
