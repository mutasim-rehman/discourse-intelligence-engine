"""YouTube transcript fetching utilities."""

import re
from urllib.parse import parse_qs, urlparse


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
