"""V7 Native Layer: lightweight heuristics for cultural/authority signals.

When translation is used, this module analyzes the original language text
for structural markers (honorifics, formal markers) that suggest authority
or aggressive intent. Used to set nativeIntentStronger when the original
tone appears stronger than the English translation conveys.
"""

from __future__ import annotations


# Language codes supported for native signal analysis
NATIVE_SIGNAL_LANGUAGES = frozenset({"ko", "ja", "zh", "zh-cn", "zh-tw"})


def _japanese_authority_signals(text: str) -> tuple[float, list[str]]:
    """Simple heuristics for Japanese: formal/honorific markers suggesting authority."""
    signals: list[str] = []
    score = 0.0

    # Formal verb endings and honorifics (romanized)
    patterns = [
        ("です", 0.2),
        ("ます", 0.15),
        ("ございます", 0.25),
        ("なさい", 0.2),  # imperative
        ("ください", 0.15),
        ("べき", 0.2),  # should/ought
        ("ね", 0.05),
        ("よ", 0.05),
    ]
    for pat, weight in patterns:
        if pat in text:
            score = min(1.0, score + weight)
            signals.append(f"formal:{pat}")

    # Aggressive/authoritative markers
    if any(p in text for p in ["しろ", "しなさい", "なさい"]):
        score = min(1.0, score + 0.3)
        signals.append("imperative")
    if "絶対" in text or "必須" in text:
        score = min(1.0, score + 0.2)
        signals.append("absolutist")

    return min(1.0, score), signals[:5]


def _korean_authority_signals(text: str) -> tuple[float, list[str]]:
    """Simple heuristics for Korean: honorific/formal markers suggesting authority."""
    signals: list[str] = []
    score = 0.0

    # Formal endings (romanized/hangul)
    patterns = [
        ("습니다", 0.2),
        ("ㅂ니다", 0.2),
        ("세요", 0.2),
        ("십시오", 0.25),
        ("해요", 0.1),
        ("세요", 0.15),
        ("시다", 0.2),
    ]
    for pat, weight in patterns:
        if pat in text:
            score = min(1.0, score + weight)
            signals.append(f"formal:{pat}")

    if "필수" in text or "반드시" in text:
        score = min(1.0, score + 0.2)
        signals.append("absolutist")

    return min(1.0, score), signals[:5]


def _chinese_authority_signals(text: str) -> tuple[float, list[str]]:
    """Simple heuristics for Chinese: formal/authority markers."""
    signals: list[str] = []
    score = 0.0

    patterns = [
        ("必须", 0.25),
        ("应该", 0.2),
        ("应当", 0.2),
        ("必须", 0.25),
        ("务必", 0.2),
        ("一定", 0.15),
    ]
    for pat, weight in patterns:
        if pat in text:
            score = min(1.0, score + weight)
            signals.append(f"formal:{pat}")

    return min(1.0, score), signals[:5]


def analyze_native_intent(original_text: str, language: str) -> tuple[float, list[str]]:
    """Analyze original language for authority/aggressive signals.

    Returns:
        (native_intent_score, native_signals)
        - native_intent_score: 0-1, higher = stronger authority/formal tone
        - native_signals: list of short labels
    """
    if not original_text or not original_text.strip():
        return 0.0, []

    lang = (language or "").lower().split("-")[0]
    if lang not in NATIVE_SIGNAL_LANGUAGES:
        return 0.0, []

    if lang == "ja":
        return _japanese_authority_signals(original_text)
    if lang == "ko":
        return _korean_authority_signals(original_text)
    if lang == "zh":
        return _chinese_authority_signals(original_text)

    return 0.0, []


def native_intent_stronger(
    original_text: str,
    translated_text: str,
    language: str,
    *,
    threshold: float = 0.35,
) -> bool:
    """Determine if native tone appears stronger than translation suggests.

    Compares native_intent_score from original text with a simple heuristic
    on translated text (e.g., imperative/formal density). Returns True when
    native signals suggest more authoritative/aggressive tone than the
    English translation conveys.

    Args:
        original_text: Source language text.
        translated_text: English translation.
        language: Source language code (e.g. ja, ko).
        threshold: Minimum native_intent_score for nativeIntentStronger.

    Returns:
        True if native tone appears stronger than translation.
    """
    native_score, native_signals = analyze_native_intent(original_text, language)
    if native_score < threshold or not native_signals:
        return False

    # Simple heuristic: if translation has few imperative/formal markers
    # relative to length, and native has strong signals -> native stronger
    trans_lower = translated_text.lower()
    trans_formal_count = sum(
        1 for w in ("must", "should", "shall", "will not", "cannot")
        if w in trans_lower
    )
    trans_len = len(translated_text.split())
    trans_formal_ratio = trans_formal_count / max(trans_len, 1)
    if native_score > 0.5 and trans_formal_ratio < 0.02:
        return True
    if native_score > 0.7:
        return True
    return False
