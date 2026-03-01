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
        if args.export_viz:
            export_viz_to_json(arc["viz"], args.export_viz)


if __name__ == "__main__":
    main()
