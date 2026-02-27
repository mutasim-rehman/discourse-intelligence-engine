"""CLI entry point: interactive text input and analysis report."""

import sys

from discourse_engine import run_pipeline, format_report


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
    if len(sys.argv) > 1:
        # Text from command-line args
        text = " ".join(sys.argv[1:])
    elif not sys.stdin.isatty():
        # Piped input
        text = read_text_piped()
    else:
        # Interactive prompt
        text = read_text_interactive()

    if not text.strip():
        print("No text provided.", file=sys.stderr)
        sys.exit(1)

    report = run_pipeline(text)
    print()
    print(format_report(report))


if __name__ == "__main__":
    main()
