"""Utility functions."""
import json
import re


def validate_email(email: str) -> bool:
    """Check if a string is a valid email format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def format_currency(amount):
    """Format a number as USD currency."""
    if amount is None:
        return "$0.00"
    return f"${amount:.2f}"


def truncate_string(s: str, max_length: int) -> str:
    """Truncate a string to a maximum length."""
    if len(s) <= max_length:
        return s
    return s[:max_length] + "..."


def calculate_percentage(value, total):
    """Calculate value as a percentage of total."""
    # BUG: no zero check — ZeroDivisionError when total == 0
    return (value / total) * 100


def sanitize_input(text: str) -> str:
    """Remove potentially dangerous characters from user input."""
    return re.sub(r"[<>\"'%;()&+]", "", text)


def parse_json_safe(text: str):
    """Parse JSON; return None on failure.

    This is a deliberate API choice — callers check the return value
    rather than catching an exception.
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None