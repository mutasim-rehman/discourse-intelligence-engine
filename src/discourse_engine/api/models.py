from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    RAW_TEXT = "raw_text"
    FILE = "file"
    YOUTUBE = "youtube"


class AnalyzeRequest(BaseModel):
    sourceType: SourceType = Field(
        description="Input source type: raw_text, file, or youtube."
    )
    rawText: Optional[str] = Field(
        default=None, description="Raw text to analyze when sourceType is raw_text."
    )
    filePath: Optional[str] = Field(
        default=None,
        description=(
            "Server-side text file path when sourceType is file. "
            "For now, this expects a readable .txt path on the backend."
        ),
    )
    youtubeUrl: Optional[str] = Field(
        default=None,
        description="YouTube URL or ID when sourceType is youtube.",
    )


class CharacterSummary(BaseModel):
    id: str
    name: str
    description: Optional[str] = None


class CharacterArcSegment(BaseModel):
    characterId: str
    arcId: str
    label: str
    startIndex: int
    endIndex: int
    confidence: float
    colorFamily: Optional[str] = None


class AnalysisFamily(str, Enum):
    ASSUMPTION = "assumption"
    AGENDA = "agenda"
    FALLACY = "fallacy"


class AnalysisSegment(BaseModel):
    startIndex: int
    endIndex: int
    text: str
    family: AnalysisFamily
    subfamily: Optional[str] = None
    confidence: float


class ColorLegendEntry(BaseModel):
    family: AnalysisFamily
    subfamily: Optional[str] = None
    color: str


class YouTubeVideoMetadata(BaseModel):
    """Video metadata when source is YouTube (for thumbnail and title display)."""
    videoId: str
    title: Optional[str] = None
    thumbnailUrl: Optional[str] = None


class DiscourseAnalysisResponse(BaseModel):
    segments: List[AnalysisSegment]
    colorLegend: List[ColorLegendEntry]
    mermaidMmd: Optional[str]
    originalText: str
    translatedText: Optional[str] = None
    originalTextLanguage: Optional[str] = None
    nativeIntentStronger: Optional[bool] = None
    youtubeVideo: Optional[YouTubeVideoMetadata] = None


class CharacterArcsResponse(BaseModel):
    characters: List[CharacterSummary]
    arcs: List[CharacterArcSegment]
    documentArcsJson: dict
    mermaidMmd: Optional[str]
    originalText: str
    translatedText: Optional[str] = None
    originalTextLanguage: Optional[str] = None
    nativeIntentStronger: Optional[bool] = None
    youtubeVideo: Optional[YouTubeVideoMetadata] = None


class TimestampedSegment(BaseModel):
    """Snippet-level alignment for YouTube transcripts (V7 Vocal Stress Sync)."""
    start: float
    end: float
    originalText: str
    translatedText: str
