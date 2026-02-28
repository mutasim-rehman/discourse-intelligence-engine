"""CLI entry point: interactive text input, YouTube video, or piped input."""

import argparse
import sys

from discourse_engine import run_pipeline, format_report


def fetch_youtube_transcript(url_or_id: str) -> str:
    """Fetch transcript from a YouTube video URL or video ID."""
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

    args = parser.parse_args()

    if args.youtube:
        try:
            print("Fetching transcript...", file=sys.stderr)
            text = fetch_youtube_transcript(args.youtube)
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

    report = run_pipeline(text)
    print()
    print(format_report(report))


if __name__ == "__main__":
    main()
