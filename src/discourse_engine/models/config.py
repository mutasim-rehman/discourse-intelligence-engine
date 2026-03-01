"""Configuration for pipeline and LLM integration."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Pipeline and analyzer configuration."""

    llm_api_key: str | None = None
    llm_model: str = "gpt-4"
    lexicon_dir: Path | None = None
    llm_enhance: bool = False
    ollama_model: str | None = None
    ollama_base: str = "http://localhost:11434"

    def __post_init__(self) -> None:
        if self.lexicon_dir is None:
            self.lexicon_dir = Path(__file__).parent.parent / "lexicons"
