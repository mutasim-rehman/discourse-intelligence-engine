"""Tests for YouTube transcript utilities."""

import pytest

from discourse_engine.utils.youtube import extract_video_id, fetch_transcript


def test_extract_video_id_from_watch_url() -> None:
    """Extract video ID from standard watch URL."""
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_from_youtu_be() -> None:
    """Extract video ID from youtu.be short URL."""
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_from_embed() -> None:
    """Extract video ID from embed URL."""
    assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_raw_id() -> None:
    """Raw 11-char ID is returned as-is."""
    assert extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_invalid_returns_none() -> None:
    """Invalid or empty input returns None."""
    assert extract_video_id("") is None
    assert extract_video_id("   ") is None
    assert extract_video_id("not-a-valid-url") is None


def test_fetch_transcript_requires_valid_id() -> None:
    """fetch_transcript raises ValueError for invalid input."""
    with pytest.raises(ValueError, match="Could not extract"):
        fetch_transcript("")


def test_fetch_transcript_integration() -> None:
    """Fetch transcript from a known video (Rick Astley - has captions)."""
    text, _ = fetch_transcript("dQw4w9WgXcQ")
    assert len(text) > 100
    assert "never" in text.lower() or "give" in text.lower()
