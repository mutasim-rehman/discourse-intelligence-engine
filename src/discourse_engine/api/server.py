from __future__ import annotations

from pathlib import Path
from typing import List
import argparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from discourse_engine import Report
from discourse_engine.models.report import AssumptionFlag, AgendaFlag, FallacyFlag
from discourse_engine.utils.youtube import fetch_transcript_only, get_video_metadata
from discourse_engine.v5.mermaid import discourse_map_to_mermaid
from discourse_engine.v5.visualization import social_graph_view
from discourse_engine.v6.arcs import arcs_to_view_payload
from discourse_engine.v6.arcs_pipeline import build_character_arcs
from discourse_engine.v6.cli import run_single_document

from .models import (
    AnalyzeRequest,
    AnalysisFamily,
    AnalysisSegment,
    CharacterArcSegment,
    CharacterArcsResponse,
    CharacterSummary,
    ColorLegendEntry,
    DiscourseAnalysisResponse,
    SourceType,
    YouTubeVideoMetadata,
)


app = FastAPI(title="Discourse Intelligence Engine API", version="0.1.0")

# Allow the Vite dev server and other frontends to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _resolve_text(req: AnalyzeRequest) -> str:
    """Resolve input text based on the requested source type."""
    if req.sourceType is SourceType.RAW_TEXT:
        if not (req.rawText and req.rawText.strip()):
            raise HTTPException(status_code=400, detail="rawText is required for raw_text sourceType.")
        return req.rawText

    if req.sourceType is SourceType.YOUTUBE:
        if not (req.youtubeUrl and req.youtubeUrl.strip()):
            raise HTTPException(status_code=400, detail="youtubeUrl is required for youtube sourceType.")
        try:
            return fetch_transcript_only(req.youtubeUrl)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if req.sourceType is SourceType.FILE:
        if not (req.filePath and req.filePath.strip()):
            raise HTTPException(
                status_code=400,
                detail=(
                    "filePath is required for file sourceType and must be a readable .txt "
                    "path on the backend for now."
                ),
            )
        path = Path(req.filePath)
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=400, detail=f"File not found: {req.filePath}")
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="utf-8", errors="ignore")

    raise HTTPException(status_code=400, detail=f"Unsupported sourceType: {req.sourceType}")


def _build_mermaid_for_map(dm) -> str | None:
    """Build a Mermaid diagram string from a V5 discourse map."""
    if dm is None:
        return None
    try:
        data = dm.to_dict()
        data.setdefault("views", {})
        data["views"]["social_graph"] = social_graph_view(dm)
        return discourse_map_to_mermaid(data)
    except Exception:
        return None


def _segments_from_report(text: str, report: Report) -> List[AnalysisSegment]:
    """Convert Report fallacies, assumptions, and agenda flags into highlight segments."""
    segments: List[AnalysisSegment] = []
    lower_text = text.lower()

    def _find_span(sentence: str) -> tuple[int, int] | None:
        s = (sentence or "").strip()
        if not s:
            return None
        s_lower = s.lower()
        idx = lower_text.find(s_lower)
        if idx == -1:
            return None
        return idx, idx + len(s)

    # Hidden assumptions
    for a in report.hidden_assumptions:
        if not isinstance(a, AssumptionFlag):
            continue
        span = _find_span(a.sentence)
        if not span:
            continue
        start, end = span
        segments.append(
            AnalysisSegment(
                startIndex=start,
                endIndex=end,
                text=text[start:end],
                family=AnalysisFamily.ASSUMPTION,
                subfamily="assumption",
                confidence=float(a.confidence or 0.7),
            )
        )

    # Hidden agenda flags
    for flag in report.hidden_agenda_flags:
        if not isinstance(flag, AgendaFlag):
            continue
        span = _find_span(flag.sentence)
        if not span:
            continue
        start, end = span
        segments.append(
            AnalysisSegment(
                startIndex=start,
                endIndex=end,
                text=text[start:end],
                family=AnalysisFamily.AGENDA,
                subfamily=str(flag.technique or flag.family or "agenda"),
                confidence=float(flag.confidence or 0.7),
            )
        )

    # Logical fallacy flags
    for f in report.logical_fallacy_flags:
        if not isinstance(f, FallacyFlag):
            continue
        span = _find_span(f.sentence)
        if not span:
            continue
        start, end = span
        segments.append(
            AnalysisSegment(
                startIndex=start,
                endIndex=end,
                text=text[start:end],
                family=AnalysisFamily.FALLACY,
                subfamily=str(getattr(f, "fallacy_type", None) or f.name or "fallacy"),
                confidence=float(f.confidence or 0.7),
            )
        )

    return segments


def _run_all_engines(text: str, document_id: str = "api:doc") -> tuple[Report, object | None]:
    """Run the full v6 single-document pipeline (v3+v4+v5+v6) with LLM enhancement enabled.

    Mirrors the CLI behavior of `discourse-engine analyze` for a single document:
    - Uses run_single_document to:
      * run the base pipeline (statistics, tone, fallacies, assumptions, agendas, satire)
      * optionally run v4 dialogue analysis and promote its signals
      * build a v5 DiscourseMap for structural views
    - Enables LLM enhancement via Ollama (llama3.2:3b) for assumptions and satire/irony.
    """
    args = argparse.Namespace(
        # v3 narrative arc / visualization (kept off for API; can be turned on later)
        v3=False,
        export_viz=None,
        # v4 dialogue promotion into main report
        dialogue=True,
        dialogue_json=None,
        # LLM enhancement configuration
        llm_enhance=True,
        ollama_model="llama3.2:3b",
        ollama_base="http://localhost:11434",
    )

    report, discourse_map = run_single_document(
        text=text,
        args=args,
        document_id=document_id,
        context_note=None,
    )
    return report, discourse_map


@app.post("/api/analysis/discourse", response_model=DiscourseAnalysisResponse)
def analyze_discourse(req: AnalyzeRequest) -> DiscourseAnalysisResponse:
    """Analyze a text for hidden assumptions, agendas, and logical fallacies."""
    text = _resolve_text(req)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Input text is empty after preprocessing.")

    # Run the unified v6 single-document path with v3+v4+v5+v6 and LLM enhancement.
    report, discourse_map = _run_all_engines(text)
    segments = _segments_from_report(text, report)

    color_legend: List[ColorLegendEntry] = [
        ColorLegendEntry(family=AnalysisFamily.ASSUMPTION, subfamily="assumption", color="#facc15"),
        ColorLegendEntry(family=AnalysisFamily.AGENDA, subfamily=None, color="#38bdf8"),
        ColorLegendEntry(family=AnalysisFamily.FALLACY, subfamily=None, color="#fb7185"),
    ]

    mermaid = _build_mermaid_for_map(discourse_map)

    youtube_video = None
    if req.sourceType == SourceType.YOUTUBE and req.youtubeUrl:
        try:
            meta = get_video_metadata(req.youtubeUrl)
            if meta.get("video_id") and meta.get("thumbnail_url"):
                youtube_video = YouTubeVideoMetadata(
                    videoId=meta["video_id"],
                    title=meta.get("title"),
                    thumbnailUrl=meta["thumbnail_url"],
                )
        except Exception:
            pass

    return DiscourseAnalysisResponse(
        segments=segments,
        colorLegend=color_legend,
        mermaidMmd=mermaid,
        originalText=text,
        youtubeVideo=youtube_video,
    )


@app.post("/api/character-arcs/analyze", response_model=CharacterArcsResponse)
def analyze_character_arcs(req: AnalyzeRequest) -> CharacterArcsResponse:
    """Analyze a text for character arcs and return a compact view for the frontend."""
    text = _resolve_text(req)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Input text is empty after preprocessing.")

    # Reuse the unified v6 path to obtain a V5 discourse map.
    _, dm = _run_all_engines(text)
    if dm is None:
        raise HTTPException(status_code=500, detail="Failed to build discourse map for character arcs.")

    # Run v4 dialogue parsing so we get turn-based points and events (novels, transcripts, etc.).
    dialogue_report = None
    try:
        from discourse_engine.v4.dialogue_pipeline import run_dialogue_from_text
        dialogue_report = run_dialogue_from_text(text)
    except Exception:
        pass

    char_arcs = build_character_arcs(dm, dialogue_report=dialogue_report, document_id="api:doc")
    arcs_payload = arcs_to_view_payload(char_arcs)

    characters: List[CharacterSummary] = []
    arc_segments: List[CharacterArcSegment] = []

    for cid, arc_dict in arcs_payload.get("characters", {}).items():
        display_name = arc_dict.get("display_name") or cid
        characters.append(
            CharacterSummary(
                id=str(cid),
                name=str(display_name),
                description=None,
            )
        )
        points = arc_dict.get("points") or []
        events = arc_dict.get("events") or []

        # Approximate character arc highlight segments from timeline points.
        for idx, pt in enumerate(points):
            position = float(pt.get("position", 0.0))
            char_index = int(position * max(len(text) - 1, 1))
            window = max(50, min(200, len(text) // 5 or 50))
            start = max(0, char_index - window // 2)
            end = min(len(text), start + window)
            label = str(pt.get("metrics", {}).get("tactic_label", "arc"))
            confidence = float(pt.get("metrics", {}).get("authority_score", 0.7))

            arc_segments.append(
                CharacterArcSegment(
                    characterId=str(cid),
                    arcId=f"{cid}:{idx}",
                    label=label,
                    startIndex=start,
                    endIndex=end,
                    confidence=confidence,
                    colorFamily=None,
                )
            )

        # Optionally, events could become additional segments in the future.

    mermaid = _build_mermaid_for_map(dm)

    youtube_video = None
    if req.sourceType == SourceType.YOUTUBE and req.youtubeUrl:
        try:
            meta = get_video_metadata(req.youtubeUrl)
            if meta.get("video_id") and meta.get("thumbnail_url"):
                youtube_video = YouTubeVideoMetadata(
                    videoId=meta["video_id"],
                    title=meta.get("title"),
                    thumbnailUrl=meta["thumbnail_url"],
                )
        except Exception:
            pass

    return CharacterArcsResponse(
        characters=characters,
        arcs=arc_segments,
        documentArcsJson=arcs_payload,
        mermaidMmd=mermaid,
        originalText=text,
        youtubeVideo=youtube_video,
    )

