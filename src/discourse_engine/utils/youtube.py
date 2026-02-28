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


def fetch_transcript(url_or_id: str, languages: list[str] | None = None) -> str:
    """Fetch transcript from a YouTube video and return as plain text.

    Args:
        url_or_id: YouTube URL or 11-character video ID.
        languages: Preferred language codes (e.g. ['en', 'de']). Defaults to ['en'].

    Returns:
        Plain text transcript.

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
    return " ".join(texts).replace("\n", " ").strip()
