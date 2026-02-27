"""Text preprocessing and tokenization helpers."""

import re


def count_words(text: str) -> int:
    """Count words in text using whitespace split."""
    if not text or not text.strip():
        return 0
    return len(text.split())


def count_sentences(text: str) -> int:
    """Count sentences using period, exclamation, question mark boundaries."""
    if not text or not text.strip():
        return 0
    # Split on sentence-ending punctuation followed by whitespace
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return len([p for p in parts if p.strip()])
