# Discourse Intelligence Engine

An NLP-driven system for analyzing the structural logic and ideological patterns embedded in language. The engine identifies hidden assumptions, logical fallacies, emotional trigger words, hidden agendas, tone shifts, and framing strategies across political discourse, interviews, novels, and film scripts.

## Features

- **Basic statistics**: Word and sentence counts
- **Trigger word profile**: Fear, authority, and identity framing levels (lexicon-based)
- **Tone summary**: Urgent, defensive, fear-oriented
- **Modal and pronoun analysis**: Authority usage and in-group/out-group framing
- **Logical fallacy flags**: Pattern-based detection (false dilemma, appeal to fear, ad hominem)
- **Hidden assumption extraction**: Rule-based (presuppositions, enthymemes, epistemic shortcuts)
- **Hidden agenda flags**: Rule-based (deflecting, dividing, asserting, personalizing, framing)

## Installation

```bash
pip install -e .
```

## Usage

### CLI

```bash
# Interactive: paste text, blank line when done
python -m discourse_engine
# or: discourse-engine

# From args or pipe
python -m discourse_engine "Either we pass this law, or our nation will collapse."
echo "Your text here" | python -m discourse_engine
```

### Python API

```python
from discourse_engine import run_pipeline, format_report

text = """
Either we pass this law, or our nation will collapse.
We must protect our people from this growing threat.
They want to destroy everything we stand for.
"""

report = run_pipeline(text)
print(format_report(report))
```

## Project Structure

```
src/discourse_engine/
├── main.py           # Pipeline entry point and report formatting
├── models/           # Report, Config, TriggerProfile, FallacyFlag, AgendaFlag
├── analyzers/        # Modular analysis components (7 analyzers)
├── lexicons/         # JSON keyword lists (fear, authority, identity)
└── utils/            # Text preprocessing helpers
```

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Detailed description of each layer, underlying logic, and examples
- **[FUTURE_WORK.md](FUTURE_WORK.md)** — Features not yet implemented and planned enhancements

## Extensibility

- Add new analyzers by implementing the analysis interface
- Swap or extend lexicon JSON files for domain-specific vocabularies
- Configure optional LLM provider for future hidden-assumption enhancement
