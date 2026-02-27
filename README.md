# Discourse Intelligence Engine

An NLP-driven system for analyzing the structural logic and ideological patterns embedded in language. The engine identifies hidden assumptions, logical fallacies, emotional trigger words, tone shifts, and framing strategies across political discourse, interviews, novels, and film scripts.

## Features

- **Basic statistics**: Word and sentence counts
- **Trigger word profile**: Fear, authority, and identity framing levels
- **Tone summary**: Urgent, defensive, fear-oriented, etc.
- **Modal and pronoun analysis**: Authority usage and in-group/out-group framing
- **Logical fallacy flags**: Pattern-based detection (false dilemma, appeal to fear, ad hominem)
- **Hidden assumption extraction**: LLM-based (stub in skeleton; extend with API)

## Installation

```bash
pip install -e .
```

## Usage

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
├── main.py           # Pipeline entry point
├── models/           # Report, config, data models
├── analyzers/        # Modular analysis components
├── lexicons/         # Keyword lists for trigger/fallacy detection
└── utils/            # Text preprocessing helpers
```

## Extensibility

- Add new analyzers by implementing the `Analyzer` protocol
- Swap lexicon JSON files for domain-specific vocabularies
- Configure LLM provider and model for hidden assumption extraction
