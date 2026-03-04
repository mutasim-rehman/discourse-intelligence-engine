"""CLI entry point: interactive text input, YouTube video, or piped input."""

import argparse
import os
import sys

from discourse_engine import run_pipeline, format_report
from discourse_engine.models.config import Config


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


def main() -> None:
    """Prompt for text, run pipeline, print report."""
    parser = argparse.ArgumentParser(
        description="Discourse Intelligence Engine - analyze text or YouTube videos for structural logic and ideological patterns.",
        epilog="Examples:\n"
        "  discourse-engine --youtube https://www.youtube.com/watch?v=VIDEO_ID\n"
        "  discourse-engine -y VIDEO_ID\n"
        "  discourse-engine \"Your text to analyze...\"\n"
        "  echo \"Your text\" | discourse-engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-y",
        "--youtube",
        metavar="URL_OR_ID",
        help="Analyze a YouTube video by URL or video ID (fetches transcript)",
    )
    parser.add_argument(
        "text",
        nargs="*",
        help="Text to analyze (ignored when using --youtube)",
    )
    parser.add_argument(
        "--v3",
        action="store_true",
        help="Enable v3 Narrative Arc & Power Dynamics analysis",
    )
    parser.add_argument(
        "--dialogue",
        action="store_true",
        help="Enable v4 dialogue analysis on speaker-tagged transcripts (Speaker: text)",
    )
    parser.add_argument(
        "--export-viz",
        metavar="PATH",
        help="Export v3 visualization data to JSON file",
    )
    parser.add_argument(
        "--llm-enhance",
        action="store_true",
        help="Enable optional LLM enhancement for subtle irony and assumptions (requires OPENAI_API_KEY or --ollama-model)",
    )
    parser.add_argument(
        "--ollama-model",
        metavar="MODEL",
        help="Ollama model for LLM enhancement (e.g. llama3.2:3b)",
    )
    parser.add_argument(
        "--dialogue-json",
        metavar="PATH",
        help="Export v4 dialogue analysis to JSON file",
    )

    args = parser.parse_args()

    context_note: str | None = None
    if args.youtube:
        try:
            print("Fetching transcript...", file=sys.stderr)
            text, context_note = fetch_youtube_transcript(args.youtube)
            print(f"Transcript length: {len(text)} chars\n", file=sys.stderr)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
    elif args.text:
        text = " ".join(args.text)
    elif not sys.stdin.isatty():
        text = read_text_piped()
    else:
        text = read_text_interactive()

    if not text.strip():
        print("No text provided.", file=sys.stderr)
        sys.exit(1)

    config = Config(
        llm_enhance=args.llm_enhance,
        ollama_model=args.ollama_model,
        llm_api_key=os.environ.get("OPENAI_API_KEY") if args.llm_enhance else None,
    )
    report = run_pipeline(text, config=config, context_note=context_note)

    # When --dialogue: promote per-turn fallacy flags into the main report so they appear in Logical Fallacy Flags.
    if args.dialogue or args.dialogue_json:
        from discourse_engine.v4.dialogue_pipeline import parse_speaker_tagged_text
        from discourse_engine.analyzers.logical_fallacy import LogicalFallacyAnalyzer

        try:
            dialogue = parse_speaker_tagged_text(text)
            existing_sentences = {f.sentence.strip().lower()[:200] for f in report.logical_fallacy_flags}
            for turn in dialogue.turns:
                turn_flags = LogicalFallacyAnalyzer().analyze(turn.text or "")
                for flag in turn_flags:
                    key = flag.sentence.strip().lower()[:200]
                    if key not in existing_sentences:
                        existing_sentences.add(key)
                        report.logical_fallacy_flags.append(flag)
        except Exception:
            pass

    print()
    print(format_report(report))

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
            export_viz_to_json(arc["viz"], args.export_viz)

    if args.dialogue or args.dialogue_json:
        from discourse_engine.v4.dialogue_pipeline import (
            run_dialogue_from_text,
            dialogue_report_to_dict,
            format_dialogue_report,
        )
        import json

        dialogue_report = run_dialogue_from_text(text)
        if args.dialogue:
            print()
            print(format_dialogue_report(dialogue_report))
        if args.dialogue_json:
            data = dialogue_report_to_dict(dialogue_report)
            with open(args.dialogue_json, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"\nExported v4 dialogue analysis to {args.dialogue_json}", file=sys.stderr)


if __name__ == "__main__":
    main()
