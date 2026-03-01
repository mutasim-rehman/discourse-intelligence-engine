"""Text preprocessing and tokenization helpers."""

import re


def split_sentences(text: str) -> list[str]:
    """Split text into sentences. Uses same logic as split_sentences_with_offsets."""
    if not text or not text.strip():
        return []
    return [s for s, _, _ in split_sentences_with_offsets(text)]


def split_sentences_with_offsets(text: str) -> list[tuple[str, int, int]]:
    """Split text into sentences with (sentence, start_offset, end_offset).

    Avoids splitting on abbreviations (e.g. a.m., p.m., U.S.) by requiring
    the sentence-ending period to not be followed by a word character.
    """
    if not text or not text.strip():
        return []
    result: list[tuple[str, int, int]] = []
    # Don't split on period when followed by letter (a.m., p.m., U.S., etc.)
    pattern = re.compile(r"([^.!?]*[.!?])(?!\w)(?:\s+|$)", re.DOTALL)
    for m in pattern.finditer(text):
        s = m.group(1).strip()
        # Skip abbreviation fragments like "m." or "a." from "3 a.m."
        if s and len(s) > 2:
            result.append((s, m.start(1), m.end(1)))
        elif s and result:
            # Merge very short fragment (likely abbrev) with previous sentence
            prev_sent, prev_start, prev_end = result[-1]
            result[-1] = (f"{prev_sent} {s}".strip(), prev_start, m.end(1))
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
    """Count sentences using same logic as split_sentences."""
    return len(split_sentences(text))
