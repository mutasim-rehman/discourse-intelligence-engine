"""V7 translation utilities for multi-language text and documents."""

from __future__ import annotations


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

    async def _translate() -> str:
        from googletrans import Translator
        async with Translator() as translator:
            result = await translator.translate(
                text, dest="en", src=source_lang or "auto"
            )
            return result.text if result and result.text else text

    try:
        return asyncio.run(_translate())
    except ImportError:
        pass
    except Exception:
        pass

    return text


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
