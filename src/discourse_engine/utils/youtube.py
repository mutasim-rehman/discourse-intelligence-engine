"""YouTube transcript fetching utilities."""

import json
import re
from urllib.parse import parse_qs, urlparse, quote
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


def extract_video_id(url_or_id: str) -> str | None:
    """Extract YouTube video ID from a URL or return the string if it's already an ID.

    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/v/VIDEO_ID
    - VIDEO_ID (11-character ID)
    """
    s = url_or_id.strip()
    if not s:
        return None

    # Already a video ID (11 chars, alphanumeric + - _)
    if re.match(r"^[\w-]{11}$", s):
        return s

    # youtu.be short format
    if "youtu.be/" in s:
        match = re.search(r"youtu\.be/([\w-]+)", s)
        return match.group(1) if match else None

    # Standard YouTube URLs
    parsed = urlparse(s)
    if "youtube.com" in parsed.netloc or "youtu.be" in parsed.netloc:
        if "v=" in parsed.query:
            qs = parse_qs(parsed.query)
            vid = qs.get("v", [None])[0]
            return vid if vid and len(vid) == 11 else None
        # /embed/VIDEO_ID or /v/VIDEO_ID
        match = re.search(r"/(?:embed|v)/([\w-]{11})", parsed.path)
        return match.group(1) if match else None

    return None


def get_video_metadata(url_or_id: str) -> dict[str, str | None]:
    """Fetch video title and thumbnail URL for display.

    Uses YouTube oEmbed when possible; falls back to deterministic thumbnail URL
    if oEmbed fails (e.g. private video, no network). Returns dict with keys:
    - video_id: str
    - title: str | None (None if oEmbed failed)
    - thumbnail_url: str (always set from video_id if not from oEmbed)
    """
    video_id = extract_video_id(url_or_id)
    if not video_id:
        return {"video_id": "", "title": None, "thumbnail_url": None}

    # Deterministic thumbnail (works even when oEmbed fails)
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

    canonical_url = f"https://www.youtube.com/watch?v={video_id}"
    oembed_url = f"https://www.youtube.com/oembed?url={quote(canonical_url)}&format=json"
    title = None
    try:
        req = Request(oembed_url, headers={"User-Agent": "DiscourseEngine/1.0"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            title = data.get("title") or None
            # Prefer oEmbed thumbnail when available (often higher quality)
            if data.get("thumbnail_url"):
                thumbnail_url = data["thumbnail_url"]
    except (URLError, HTTPError, json.JSONDecodeError, KeyError, OSError):
        pass

    return {
        "video_id": video_id,
        "title": title,
        "thumbnail_url": thumbnail_url,
    }


def fetch_transcript(url_or_id: str, languages: list[str] | None = None) -> tuple[str, str | None]:
    """Fetch transcript from a YouTube video and return cleaned text plus optional context note.

    Args:
        url_or_id: YouTube URL or 11-character video ID.
        languages: Preferred language codes (e.g. ['en', 'de']). Defaults to ['en'].

    Returns:
        (cleaned_text, context_note): cleaned transcript and optional interpretation note
        (e.g. when comedic/satirical context is detected).

    Raises:
        ValueError: If video ID cannot be extracted or transcript is unavailable.
    """
    from youtube_transcript_api import (
        YouTubeTranscriptApi,
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable,
    )

    video_id = extract_video_id(url_or_id)
    if not video_id:
        raise ValueError(
            f"Could not extract YouTube video ID from: {url_or_id!r}. "
            "Provide a URL like https://www.youtube.com/watch?v=VIDEO_ID or an 11-character video ID."
        )

    if languages is None:
        languages = ["en"]

    try:
        fetched = YouTubeTranscriptApi().fetch(video_id, languages=languages)
    except TranscriptsDisabled:
        raise ValueError(f"Transcripts are disabled for video: {video_id}")
    except NoTranscriptFound:
        raise ValueError(
            f"No transcript found for video {video_id} in languages {languages}. "
            "The video may not have captions, or try different language codes."
        )
    except VideoUnavailable:
        raise ValueError(f"Video unavailable or does not exist: {video_id}")

    # FetchedTranscript is iterable; each item is FetchedTranscriptSnippet with .text
    texts = [snippet.text for snippet in fetched]
    raw = " ".join(texts).replace("\n", " ").strip()
    return preprocess_transcript(raw), detect_comedic_context(raw)


def detect_comedic_context(text: str) -> str | None:
    """Detect if text appears to be from comedy/satire (e.g. roast, correspondents' dinner).

    Returns an interpretation note if detected, else None.
    """
    lower = text.lower()
    # Transcript markers that indicate audience reaction (comedy, speeches)
    comedy_markers = (
        "[laughter]" in lower or "[laughs]" in lower or "[applause]" in lower
        or "[music]" in lower
    )
    # Explicit humor signals
    humor_phrases = (
        "just kidding" in lower or "i'm joking" in lower or "just joking" in lower
        or "that was a joke" in lower or "comedic" in lower or "satire" in lower
    )
    if comedy_markers or humor_phrases:
        return (
            "Comedic or satirical context detected (e.g. roast, comedy speech). "
            "Many flagged patterns may reflect humor, irony, or audience engagement "
            "rather than literal persuasion tactics. Interpret with caution."
        )
    return None


def preprocess_transcript(text: str) -> str:
    """Clean transcript artifacts and improve sentence boundaries for analysis.

    - Removes [Applause], [Laughter], [Music], etc. and uses them as sentence boundaries
    - Collapses extra whitespace
    - Helps sentence segmentation for transcript-style text that lacks punctuation
    """
    if not text or not text.strip():
        return text
    # Replace transcript markers with period+space to create sentence boundaries
    # This prevents run-on "sentences" and removes noise from pattern matching
    pattern = re.compile(r"\s*\[[\w\s]+\]\s*", re.IGNORECASE)
    cleaned = pattern.sub(". ", text)
    # Collapse multiple spaces and repeated periods
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\.\s*\.+", ". ", cleaned)
    cleaned = cleaned.strip()
    return cleaned


def fetch_transcript_only(url_or_id: str, languages: list[str] | None = None) -> str:
    """Fetch transcript and return only the cleaned text (no context note)."""
    text, _ = fetch_transcript(url_or_id, languages)
    return text


def fetch_transcript_with_translation(
    url_or_id: str,
) -> tuple[str, str, str, str | None, list[dict]]:
    """Fetch transcript with V7 translation: English for analysis, original for Native Layer.

    Uses YouTubeTranscriptApi().list() to access translation_languages. If English
    transcript exists, uses it directly. Otherwise fetches first available transcript
    and translates to English via transcript.translate('en').fetch().

    Returns:
        (original_text, translated_text, original_lang, context_note, timestamped_segments)
        - original_text: cleaned text in source language (for Native Layer)
        - translated_text: cleaned text in English (for V1-V6 pipeline)
        - original_lang: e.g. 'en', 'ja', 'es'
        - context_note: e.g. comedic context warning, or None
        - timestamped_segments: list of {start, end, originalText, translatedText}
          for snippet-level alignment (Vocal Stress Sync)

    Raises:
        ValueError: If video ID cannot be extracted or transcript is unavailable.
    """
    from youtube_transcript_api import (
        YouTubeTranscriptApi,
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable,
    )

    video_id = extract_video_id(url_or_id)
    if not video_id:
        raise ValueError(
            f"Could not extract YouTube video ID from: {url_or_id!r}. "
            "Provide a URL like https://www.youtube.com/watch?v=VIDEO_ID or an 11-character video ID."
        )

    try:
        transcript_list = YouTubeTranscriptApi().list(video_id)
    except TranscriptsDisabled:
        raise ValueError(f"Transcripts are disabled for video: {video_id}")
    except VideoUnavailable:
        raise ValueError(f"Video unavailable or does not exist: {video_id}")

    original_snippets = None
    translated_snippets = None
    original_lang = "en"

    # 1. Try English transcript first
    try:
        transcript = transcript_list.find_transcript(["en"])
        fetched = transcript.fetch()
        original_snippets = list(fetched)
        translated_snippets = original_snippets
        original_lang = "en"
    except NoTranscriptFound:
        pass

    # 2. Fall back: first available transcript + translate to English
    if original_snippets is None:
        transcript = next(iter(transcript_list), None)
        if transcript is None:
            raise ValueError(
                f"No transcript found for video {video_id}. "
                "The video may not have captions."
            )
        original_lang = transcript.language_code
        original_snippets = list(transcript.fetch())
        try:
            translated_transcript = transcript.translate("en")
            translated_snippets = list(translated_transcript.fetch())
        except Exception:
            translated_snippets = original_snippets

    # Build text strings
    raw_original = " ".join(s.text for s in original_snippets).replace("\n", " ").strip()
    raw_translated = " ".join(s.text for s in translated_snippets).replace("\n", " ").strip()
    original_text = preprocess_transcript(raw_original)
    translated_text = preprocess_transcript(raw_translated)
    context_note = detect_comedic_context(raw_translated)

    # Build timestamped segments for Vocal Stress Sync
    timestamped_segments: list[dict] = []
    for orig, trans in zip(original_snippets, translated_snippets):
        start = getattr(orig, "start", 0.0)
        duration = getattr(orig, "duration", 0.0)
        end = start + duration
        timestamped_segments.append({
            "start": start,
            "end": end,
            "originalText": getattr(orig, "text", ""),
            "translatedText": getattr(trans, "text", ""),
        })

    return original_text, translated_text, original_lang, context_note, timestamped_segments
