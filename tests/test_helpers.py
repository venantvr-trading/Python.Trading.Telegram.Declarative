"""Test helper utilities for type compatibility."""

from typing import Any, Dict

# Type alias for test payload to avoid type checking issues
TestPayload = Dict[str, Any]


def create_test_payload(text: str = "", reply_markup: str = "") -> TestPayload:
    """Create a test payload that mimics TelegramPayload structure."""
    return {"text": text, "reply_markup": reply_markup}


def create_test_message(text: str) -> TestPayload:
    """Create a simple test message."""
    return create_test_payload(text=text)


def create_test_messages(texts: list[str]) -> list[TestPayload]:
    """Create multiple test messages."""
    return [create_test_message(text) for text in texts]
