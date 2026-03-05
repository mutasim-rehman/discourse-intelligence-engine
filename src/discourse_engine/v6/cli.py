"""V6 unified CLI entry points for the Discourse Intelligence Engine.

This module introduces a subcommand-based CLI centered on:

- ``discourse-engine analyze``: analyze a single text, file, or a batch folder.

The implementation reuses the existing v3/v4/v5 engines and exports while
creating a clean surface for future V6 features (cross-document intelligence,
rhetorical fingerprints, etc.).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Iterable, Tuple

from discourse_engine import format_report, run_pipeline
from discourse_engine.models.config import Config
from discourse_engine.models.report import AgendaFlag, Report
from discourse_engine.v5.models import DiscourseMap
from discourse_engine.v5.library import build_library_map
from discourse_engine.v5.scene_detector import build_v5_discourse_map
from discourse_engine.v5.visualization import export_discourse_map
from discourse_engine.v6.aggregator import export_library_persona_report


def fetch_youtube_transcript(url_or_id: str) -> tuple[str, str | None]:
    """Fetch transcript from a YouTube video URL or video ID. Returns (text, context_note)."""
    from discourse_engine.utils.youtube import fetch_transcript

    return fetch_transcript(url_or_id)


def read_text_interactive() -> str:
    """Read multi-line text from stdin. Empty line ends input."""
    print("Enter text to analyze (blank line when done):")
    print("-" * 40)
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "" and lines:
            break
        if line == "":
            continue
        lines.append(line)
    return "\n".join(lines) if lines else ""


def read_text_piped() -> str:
    """Read all text from stdin (for piping)."""
    return sys.stdin.read()


def _resolve_export_path(path: str) -> str:
    """Put export artifacts into 'exports/' by default when no folder is given."""
    if not path:
        return path
    directory = os.path.dirname(path)
    if not directory:
        directory = "exports"
        full = os.path.join(directory, path)
    else:
        full = path
    os.makedirs(os.path.dirname(full), exist_ok=True)
    return full


def _default_v5_export_name(prefix: str = "v5_map") -> str:
    ts = time.strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.json"


def _resolve_v5_export_path(args: argparse.Namespace, *, default_prefix: str) -> str | None:
    """Resolve the path for v5 map export, honoring --v5-map-json and --export."""
    explicit = getattr(args, "v5_map_json", None)
    if explicit:
        return _resolve_export_path(explicit)
    if getattr(args, "export", False):
        name = _default_v5_export_name(prefix=default_prefix)
        return _resolve_export_path(name)
    return None


def _resolve_library_report_path(
    args: argparse.Namespace,
    *,
    default_dir_from_v5: str | None,
) -> str | None:
    """Resolve the path for the library persona report."""
    explicit = getattr(args, "library_report_json", None)
    if explicit:
        return _resolve_export_path(explicit)
    if default_dir_from_v5:
        return os.path.join(default_dir_from_v5, "library_report.json")
    return None


def add_analyze_subparser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the `analyze` subcommand on the given subparsers collection."""
    description = (
        "Analyze text, files, or folders for structural logic, tone, and social dynamics.\n\n"
        "Examples:\n"
        "  discourse-engine analyze \"Your text here...\" --export\n"
        "  discourse-engine analyze ./transcripts/ --batch --v5-map-json master_graph.json\n"
        "  echo \"Your text\" | discourse-engine analyze\n"
    )

    analyze = subparsers.add_parser(
        "analyze",
        help="Analyze a text, file, or folder.",
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    analyze.add_argument(
        "target",
        nargs="?",
        help=(
            "Text, file path, or folder path to analyze. "
            "When omitted, text is read from stdin or an interactive prompt."
        ),
    )
    analyze.add_argument(
        "-y",
        "--youtube",
        metavar="URL_OR_ID",
        help="Analyze a YouTube video by URL or video ID (fetches transcript).",
    )
    analyze.add_argument(
        "--batch",
        action="store_true",
        help="Treat <target> as a folder and run batch/library analysis over all files.",
    )
    analyze.add_argument(
        "--v3",
        action="store_true",
        help="Enable v3 Narrative Arc & Power Dynamics analysis.",
    )
    analyze.add_argument(
        "--dialogue",
        action="store_true",
        help="Enable v4 dialogue analysis on speaker-tagged transcripts (Speaker: text).",
    )
    analyze.add_argument(
        "--export-viz",
        metavar="PATH",
        help="Export v3 visualization data to JSON file.",
    )
    analyze.add_argument(
        "--llm-enhance",
        action="store_true",
        help=(
            "Enable optional LLM enhancement for subtle irony and assumptions "
            "(requires OPENAI_API_KEY or --ollama-model)."
        ),
    )
    analyze.add_argument(
        "--ollama-model",
        metavar="MODEL",
        help="Ollama model for LLM enhancement (e.g. llama3.2:3b).",
    )
    analyze.add_argument(
        "--dialogue-json",
        metavar="PATH",
        help="Export v4 dialogue analysis to JSON file.",
    )
    analyze.add_argument(
        "--v5-map-json",
        metavar="PATH",
        help="Export V5 discourse map (semantic graph) to JSON file.",
    )
    analyze.add_argument(
        "--library-report-json",
        metavar="PATH",
        help="Export cross-document library persona report to JSON (batch mode).",
    )
    analyze.add_argument(
        "--export",
        action="store_true",
        help=(
            "Convenience flag for exporting a V5 discourse map JSON to the 'exports/' "
            "folder with an auto-generated filename."
        ),
    )

    analyze.set_defaults(command="analyze", handler=run_analyze_from_args)


def run_analyze_from_args(args: argparse.Namespace) -> int:
    """Entry point for the `analyze` subcommand."""
    # YouTube input takes precedence over target/batch.
    if args.youtube:
        try:
            print("Fetching transcript...", file=sys.stderr)
            text, context_note = fetch_youtube_transcript(args.youtube)
            print(f"Transcript length: {len(text)} chars\n", file=sys.stderr)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 1

        report, discourse_map = run_single_document(
            text=text,
            args=args,
            document_id=f"youtube:{args.youtube}",
            context_note=context_note,
        )

        export_path = _resolve_v5_export_path(args, default_prefix="v5_map_youtube")
        if discourse_map is not None and export_path:
            export_discourse_map(discourse_map, export_path)
            print(f"\nExported v5 discourse map to {export_path}", file=sys.stderr)

        return 0

    # Non-YouTube: resolve target vs stdin vs interactive.
    stdin_has_data = not sys.stdin.isatty()
    target = args.target

    # Batch-folder mode.
    if args.batch:
        if not target:
            print("Batch mode requires a folder path as <target>.", file=sys.stderr)
            return 1

        folder = Path(target)
        if not folder.is_dir():
            print(
                f"Batch mode requires a directory target; got: {target}",
                file=sys.stderr,
            )
            return 1

        library_map = run_batch_analyze(folder, args)

        export_path = _resolve_v5_export_path(args, default_prefix="v5_library_map")
        export_dir: str | None = None
        if export_path:
            export_discourse_map(library_map, export_path)
            export_dir = os.path.dirname(export_path)
            print(
                f"\nExported v5 library discourse map to {export_path}",
                file=sys.stderr,
            )
        else:
            # No export requested; still useful to know what happened.
            print(
                f"Processed batch folder '{folder}' into a combined discourse map "
                "(no export path provided).",
                file=sys.stderr,
            )

        # Library Persona Engine: emit a library_report.json alongside the map
        # or into the default exports/ directory when no map export is requested.
        library_report_path = _resolve_library_report_path(
            args, default_dir_from_v5=export_dir or "exports"
        )
        if library_report_path:
            export_library_persona_report(library_map, library_report_path)
            print(
                f"Exported library persona report to {library_report_path}",
                file=sys.stderr,
            )

        return 0

    # Single-document mode.
    text: str
    context_note: str | None = None
    document_id = "doc:0"

    if target:
        path = Path(target)
        if path.exists() and path.is_file():
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = path.read_text(encoding="utf-8", errors="ignore")
            document_id = str(path)
        elif path.exists() and path.is_dir():
            print(
                f"Target '{target}' is a directory. Use --batch for folder analysis.",
                file=sys.stderr,
            )
            return 1
        else:
            # Treat as raw text string.
            text = target
    elif stdin_has_data:
        text = read_text_piped()
    else:
        text = read_text_interactive()

    if not text.strip():
        print("No text provided.", file=sys.stderr)
        return 1

    report, discourse_map = run_single_document(
        text=text,
        args=args,
        document_id=document_id,
        context_note=context_note,
    )

    export_path = _resolve_v5_export_path(args, default_prefix="v5_map")
    if discourse_map is not None and export_path:
        export_discourse_map(discourse_map, export_path)
        print(f"\nExported v5 discourse map to {export_path}", file=sys.stderr)

    return 0


def _build_config_from_args(args: argparse.Namespace) -> Config:
    return Config(
        llm_enhance=args.llm_enhance,
        ollama_model=args.ollama_model,
        llm_api_key=os.environ.get("OPENAI_API_KEY") if args.llm_enhance else None,
    )


def run_single_document(
    text: str,
    *,
    args: argparse.Namespace,
    document_id: str = "doc:0",
    context_note: str | None = None,
) -> tuple[Report, DiscourseMap | None]:
    """Run the full single-document analysis path and print reports."""
    config = _build_config_from_args(args)

    # Optional v4 dialogue report, reused across promotion + pretty-print.
    dialogue_report = None

    report = run_pipeline(text, config=config, context_note=context_note)

    # When --dialogue: promote v4 insights (fallacies, evasion, topic threading)
    # into the main report so they appear in Logical Fallacy Flags, Hidden Agenda,
    # and Tone.
    if args.dialogue or args.dialogue_json:
        from discourse_engine.v4.dialogue_pipeline import (
            run_dialogue_from_text,
        )
        from discourse_engine.v4.topic_tracker import TopicTracker
        from discourse_engine.analyzers.logical_fallacy import LogicalFallacyAnalyzer

        try:
            dialogue_report = run_dialogue_from_text(text)
            dialogue = dialogue_report.dialogue

            # Promote per-turn fallacy flags into the main report so they appear in Logical Fallacy Flags.
            existing_sentences = {
                f.sentence.strip().lower()[:200] for f in report.logical_fallacy_flags
            }
            for turn in dialogue.turns:
                turn_flags = LogicalFallacyAnalyzer().analyze(turn.text or "")
                for flag in turn_flags:
                    key = flag.sentence.strip().lower()[:200]
                    if key not in existing_sentences:
                        existing_sentences.add(key)
                        report.logical_fallacy_flags.append(flag)

            # Topic escalation: if key entities are dodged and never resolved, flag Intentional Topic Suppression.
            topics = TopicTracker().analyze(dialogue)
            for ent in topics.entities:
                if ent.consecutive_evasions >= 1:
                    pattern_hint = (
                        f"entity '{ent.entity}' raised but not substantively addressed "
                        f"({ent.consecutive_evasions} consecutive evasions)"
                    )
                    report.hidden_agenda_flags.append(
                        AgendaFlag(
                            family="Intentional evasion",
                            technique="Topic suppression",
                            pattern_hint=pattern_hint,
                            sentence=topics.summary,
                            confidence=0.80,
                        )
                    )

            # High evasion across the dialogue → surface as tone + agenda signal.
            if (
                dialogue_report.evasion
                and dialogue_report.evasion.aggregate_score >= 0.6
            ):
                if "Evasive" not in report.tone:
                    report.tone.append("Evasive")
                # Attach a coarse-grained agenda flag if not already present.
                summary = (
                    dialogue_report.evasion.summary
                    or "High evasion across answers."
                )
                report.hidden_agenda_flags.append(
                    AgendaFlag(
                        family="Intentional evasion",
                        technique="Answer reframing / non-answer",
                        pattern_hint=summary,
                        sentence=summary,
                        confidence=0.75,
                    )
                )
        except Exception:
            # Dialogue analysis is best-effort; do not fail the base report.
            pass

    print()
    print(format_report(report))

    # Optional v3 narrative arc when --v3 or --export-viz.
    if args.v3 or args.export_viz:
        from discourse_engine.v3.pipeline import run_narrative_arc, export_viz_to_json

        arc = run_narrative_arc(text)
        print()
        print("--- V3 Narrative Arc ---")
        print(arc["summary"])
        if arc["escalation_points"]:
            print(f"Escalation at chunks: {arc['escalation_points']}")
        if arc["framing_shifts"]:
            print("Framing shifts:", arc["framing_shifts"])
        if arc.get("logical_leaps"):
            for ll in arc["logical_leaps"]:
                print(f"Logical leap (similarity={ll['similarity']:.2f}):")
                print(f"  Problem: {ll['problem_snippet']}")
                print(f"  Solution: {ll['solution_snippet']}")
        if args.export_viz:
            export_path = _resolve_export_path(args.export_viz)
            export_viz_to_json(arc["viz"], export_path)

    # Optional v4 outputs (pretty-print and JSON).
    if args.dialogue or args.dialogue_json:
        from discourse_engine.v4.dialogue_pipeline import (
            run_dialogue_from_text,
            dialogue_report_to_dict,
            format_dialogue_report,
        )
        import json

        # Reuse the dialogue report computed above when available.
        if dialogue_report is None:
            dialogue_report = run_dialogue_from_text(text)

        if args.dialogue:
            print()
            print(format_dialogue_report(dialogue_report))
        if args.dialogue_json:
            data = dialogue_report_to_dict(dialogue_report)
            export_path = _resolve_export_path(args.dialogue_json)
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(
                f"\nExported v4 dialogue analysis to {export_path}",
                file=sys.stderr,
            )

    # Always build a V5 discourse map in single-document mode; export may be skipped.
    try:
        result = build_v5_discourse_map(text, document_id=document_id)
        dm = result.discourse_map
    except Exception:
        dm = None

    return report, dm


def _iter_folder_documents(root: Path) -> Iterable[Tuple[str, str]]:
    """Yield (document_id, text) pairs for all regular files under root."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_id = str(path.relative_to(root))
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")
        yield rel_id, text


def run_batch_analyze(folder: Path, args: argparse.Namespace) -> DiscourseMap:
    """Run batch/library analysis over all files in a folder."""
    documents = list(_iter_folder_documents(folder))
    if not documents:
        print(
            f"No regular files found under folder '{folder}'.",
            file=sys.stderr,
        )
        # Return an empty library map for callers that still want a DiscourseMap.
        return DiscourseMap()

    print(
        f"Building library discourse map from {len(documents)} documents under '{folder}'...",
        file=sys.stderr,
    )

    dm = build_library_map(documents)

    # Lightweight batch summary to stdout.
    num_speakers = sum(
        1 for node in dm.nodes.values() if getattr(node, "kind", None) == "speaker"
    )
    print()
    print("--- Batch Analysis Summary ---")
    print(f"Documents processed: {len(documents)}")
    print(f"Scenes: {len(dm.scenes)}")
    print(f"Speaker nodes: {num_speakers}")

    return dm

