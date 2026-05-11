"""Structured error response helpers per Task Statement 2.2.

The exam tests four error categories: transient, validation, business, permission.
Each error must include errorCategory, isRetryable, and a human-readable description
so the agent can make appropriate recovery decisions.
"""
from typing import Literal, TypedDict

ErrorCategory = Literal["transient", "validation", "business", "permission"]


class StructuredError(TypedDict):
    isError: bool                # MCP's isError flag
    errorCategory: ErrorCategory
    isRetryable: bool
    message: str                 # human-readable, safe to surface to customer
    detail: str                  # internal detail for logs / agent reasoning


def transient_error(message: str, detail: str = "") -> StructuredError:
    """Timeouts, service unavailability — agent should retry."""
    return {
        "isError": True,
        "errorCategory": "transient",
        "isRetryable": True,
        "message": message,
        "detail": detail,
    }


def validation_error(message: str, detail: str = "") -> StructuredError:
    """Bad input — retrying with same input will fail again."""
    return {
        "isError": True,
        "errorCategory": "validation",
        "isRetryable": False,
        "message": message,
        "detail": detail,
    }


def business_error(message: str, detail: str = "") -> StructuredError:
    """Policy violation (e.g., refund over limit) — non-retryable, customer-friendly."""
    return {
        "isError": True,
        "errorCategory": "business",
        "isRetryable": False,
        "message": message,
        "detail": detail,
    }


def permission_error(message: str, detail: str = "") -> StructuredError:
    """Auth failure — non-retryable without intervention."""
    return {
        "isError": True,
        "errorCategory": "permission",
        "isRetryable": False,
        "message": message,
        "detail": detail,
    }