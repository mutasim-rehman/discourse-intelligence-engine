"""Top-level CLI entry point for the Discourse Intelligence Engine.

V6 introduces a subcommand-based architecture. The primary entry point is:

    discourse-engine analyze ...

which is implemented in ``discourse_engine.v6.cli``.
"""

import argparse
import sys

from discourse_engine.v6.cli import add_analyze_subparser


def main(argv: list[str] | None = None) -> None:
    """Dispatch to subcommands (starting with `analyze`)."""
    parser = argparse.ArgumentParser(
        description=(
            "Discourse Intelligence Engine - analyze text, transcripts, or folders "
            "for structural logic and ideological patterns."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")
    # Require a subcommand; this is a breaking change aligned with V6.
    subparsers.required = True  # type: ignore[attr-defined]

    add_analyze_subparser(subparsers)

    args = parser.parse_args(argv)

    handler = getattr(args, "handler", None)
    if callable(handler):
        exit_code = handler(args)
    else:
        parser.print_help()
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
