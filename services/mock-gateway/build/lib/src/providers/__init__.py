from __future__ import annotations

from ..config import settings
from .base import Provider
from .anthropic import AnthropicProvider
from .mock import MockProvider


def get_provider() -> Provider:
    """Select the provider implementation based on LLM_MODE."""
    if settings.llm_mode == "anthropic":
        return AnthropicProvider()
    return MockProvider()
