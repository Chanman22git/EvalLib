from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..schemas import ChatRequest


@dataclass
class ProviderResult:
    content: str
    model: str
    finish_reason: str
    input_tokens: int
    output_tokens: int


class Provider(Protocol):
    """A model provider the gateway can proxy to."""

    name: str

    async def complete(self, req: ChatRequest, model: str) -> ProviderResult: ...
