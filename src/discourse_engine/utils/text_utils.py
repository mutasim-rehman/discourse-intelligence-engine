"""Text preprocessing and tokenization helpers."""

import re


def split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    if not text or not text.strip():
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def split_sentences_with_offsets(text: str) -> list[tuple[str, int, int]]:
    """Split text into sentences with (sentence, start_offset, end_offset)."""
    if not text or not text.strip():
        return []
    result: list[tuple[str, int, int]] = []
    pattern = re.compile(r"([^.!?]*[.!?])(?:\s+|$)", re.DOTALL)
    for m in pattern.finditer(text):
        s = m.group(1).strip()
        if s:
            result.append((s, m.start(1), m.end(1)))
    if not result and text.strip():
        result.append((text.strip(), 0, len(text)))
    return result


def sentence_containing_offset(sentences_with_offsets: list[tuple[str, int, int]], pos: int) -> str:
    """Return the sentence that contains the given character position."""
    for sent, start, end in sentences_with_offsets:
        if start <= pos < end:
            return sent
    # Fallback: return first or last
    if sentences_with_offsets:
        return sentences_with_offsets[0][0]
    return ""


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
