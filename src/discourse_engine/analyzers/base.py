"""Abstract base for pipeline analyzers."""

from typing import Protocol, TypeVar

T = TypeVar("T")


class Analyzer(Protocol[T]):
    """Protocol for analyzers: each implements analyze(text) -> result."""

    def analyze(self, text: str) -> T:
        """Analyze the given text and return structured result."""
        ...
