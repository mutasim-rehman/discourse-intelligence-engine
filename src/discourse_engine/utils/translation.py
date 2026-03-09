"""V7 translation utilities for multi-language text and documents."""

from __future__ import annotations

import re

# Google Translate has limits; use small chunks for reliability
_TRANSLATE_CHUNK_LIMIT = 600  # small chunks work better (paste-text 500 lines; transcript block fails)
_CHUNK_DELAY_SEC = 0.3  # delay between chunks to reduce rate-limit issues


def _split_by_sentences(text: str, max_chars: int = _TRANSLATE_CHUNK_LIMIT) -> list[str]:
    """Split text by sentence boundaries (Urdu ।, English .) for transcript-style blocks."""
    if len(text) <= max_chars:
        return [text] if text.strip() else []
    sentences = re.split(r"(?<=[।.])\s*", text)
    if len(sentences) <= 1 and len(text) > max_chars:
        return _split_long_paragraph(text, max_chars)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if current_len + len(s) + 1 <= max_chars:
            current.append(s)
            current_len += len(s) + 1
        else:
            if current:
                chunks.append(" ".join(current))
            if len(s) > max_chars:
                chunks.extend(_split_long_paragraph(s, max_chars))
                current, current_len = [], 0
            else:
                current, current_len = [s], len(s)
    if current:
        chunks.append(" ".join(current))
    return chunks


def _split_into_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs (double newline or single newline)."""
    text = (text or "").strip()
    if not text:
        return []
    # Prefer splitting on blank lines (paragraphs), then on single newlines (lines)
    blocks = re.split(r"\n\s*\n", text)
    paragraphs: list[str] = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        # If no internal newlines, treat as one paragraph
        if "\n" not in b:
            paragraphs.append(b)
            continue
        # Split by single newline so each line is a unit (still "paragraph-like")
        for line in b.split("\n"):
            line = line.strip()
            if line:
                paragraphs.append(line)
    return paragraphs if paragraphs else [text]


def _split_long_paragraph(paragraph: str, max_size: int) -> list[str]:
    """Split a single paragraph by length only when it exceeds max_size."""
    if len(paragraph) <= max_size:
        return [paragraph] if paragraph.strip() else []
    chunks: list[str] = []
    rest = paragraph
    while rest:
        if len(rest) <= max_size:
            chunks.append(rest)
            break
        piece = rest[:max_size]
        last_break = max(
            piece.rfind("।"),
            piece.rfind("."),
            piece.rfind(" "),
        )
        if last_break > max_size // 2:
            piece = piece[: last_break + 1].rstrip()
            rest = rest[last_break + 1 :].lstrip()
        else:
            rest = rest[max_size:]
        if piece:
            chunks.append(piece)
    return chunks


def _chunk_for_translation(text: str, max_size: int = _TRANSLATE_CHUNK_LIMIT) -> tuple[list[str], list[bool]]:
    """Split text paragraph-first; only sub-split paragraphs over max_size.

    Returns:
        (chunks, paragraph_end): chunks to send, and whether each chunk ends a paragraph.
    """
    paragraphs = _split_into_paragraphs(text)
    if not paragraphs:
        return [], []

    chunks: list[str] = []
    paragraph_end: list[bool] = []

    for p in paragraphs:
        if len(p) <= max_size:
            chunks.append(p)
            paragraph_end.append(True)
        else:
            # Use sentence-split for transcript-style blocks (no newlines)
            sub = (
                _split_by_sentences(p, max_chars=max_size)
                if "\n" not in p
                else _split_long_paragraph(p, max_size)
            )
            for i, s in enumerate(sub):
                chunks.append(s)
                paragraph_end.append(i == len(sub) - 1)
    return chunks, paragraph_end


def _chunk_for_translation_flat(text: str, max_size: int = _TRANSLATE_CHUNK_LIMIT) -> list[str]:
    """Return only the chunk list (for retry path that doesn't need paragraph boundaries)."""
    chunks, _ = _chunk_for_translation(text, max_size)
    return chunks


def detect_language(text: str) -> str:
    """Detect the language of the given text.

    Uses langdetect when available; otherwise falls back to a simple heuristic
    (assume English for ASCII-dominated text).

    Returns:
        ISO 639-1 language code, e.g. 'en', 'es', 'ja', 'ko'.
    """
    text = (text or "").strip()
    if not text:
        return "en"

    try:
        import langdetect
        return langdetect.detect(text)
    except ImportError:
        pass
    except langdetect.LangDetectException:
        return "en"

    # Fallback: assume English if mostly ASCII
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    if ascii_chars / max(len(text), 1) > 0.9:
        return "en"
    return "en"


def translate_to_english(text: str, source_lang: str | None = None) -> str:
    """Translate text to English.

    Uses googletrans when available. If translation fails or is unavailable,
    returns the original text.

    Args:
        text: Text to translate.
        source_lang: Optional source language code (e.g. 'es'). If None, auto-detects.

    Returns:
        Translated English text, or original text if translation fails.
    """
    import asyncio

    text = (text or "").strip()
    if not text:
        return text

    if source_lang and source_lang.lower() in ("en", "en-us", "en-gb"):
        return text

    async def _translate_chunk(
        translator: object, chunk: str, src: str
    ) -> str:
        """Translate one chunk; if unchanged, retry with smaller sub-chunks."""
        result = await translator.translate(
            chunk, dest="en", src=src
        )
        out = (result.text if result and result.text else "").strip()
        if out and out != chunk:
            return out
        # Chunk may have been skipped by API; retry as smaller chunks
        if len(chunk) > 200:
            sub_chunks = _chunk_for_translation_flat(chunk, max_size=200)
            sub_out: list[str] = []
            for sc in sub_chunks:
                sub_out.append(await _translate_chunk(translator, sc, src))
                await asyncio.sleep(_CHUNK_DELAY_SEC)
            return " ".join(sub_out) if sub_out else chunk
        return chunk

    async def _translate() -> str:
        from googletrans import Translator

        chunks, paragraph_end = _chunk_for_translation(text)
        if not chunks:
            return text

        async with Translator() as translator:
            translated_chunks: list[str] = []
            src = source_lang or "auto"
            for i, chunk in enumerate(chunks):
                if i > 0:
                    await asyncio.sleep(_CHUNK_DELAY_SEC)
                translated_chunks.append(
                    await _translate_chunk(translator, chunk, src)
                )
            # Rejoin with paragraph boundaries where we had them
            parts: list[str] = []
            for j, t in enumerate(translated_chunks):
                parts.append(t)
                if j < len(paragraph_end) and paragraph_end[j]:
                    parts.append("\n\n")
            return "".join(parts).rstrip() if parts else text

    try:
        return asyncio.run(_translate())
    except ImportError:
        # Testing helper: signal that googletrans is not installed/available
        return "[GOOGLETRANS_UNAVAILABLE]"
    except Exception:
        # Testing helper: signal a generic translation error instead of silently
        # falling back to the original text.
        return "[GOOGLETRANS_ERROR]"


def prepare_text_for_analysis(text: str) -> tuple[str, str | None, str]:
    """Detect language and translate to English if needed for V7 analysis.

    Args:
        text: Raw input text.

    Returns:
        (text_for_analysis, original_text, detected_lang)
        - text_for_analysis: English text (translated or original)
        - original_text: Original text when translation was used, else None
        - detected_lang: Detected ISO 639-1 code
    """
    if not (text or "").strip():
        return "", None, "en"

    detected = detect_language(text)
    if detected.lower() in ("en", "en-us", "en-gb"):
        return text, None, detected

    translated = translate_to_english(text, source_lang=detected)
    if translated and translated != text:
        return translated, text, detected
    return text, None, detected
