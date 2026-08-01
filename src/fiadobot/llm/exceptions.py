"""Exception hierarchy for the LLM integration layer."""

from __future__ import annotations

# The exception is a simple marker and intentionally lightweight.
# pylint: disable=too-few-public-methods


class LLMProviderError(Exception):
    """Raised when a configured LLM provider fails to interpret a prompt.

    Adapters translate vendor-specific failures (timeouts, rate limits,
    connectivity issues, malformed responses) into this provider-agnostic
    error so callers never need to know which vendor SDK is in use.
    """
