"""LLM-based hidden assumption extraction (stub)."""


class HiddenAssumptionExtractor:
    """
    Extracts hidden assumptions via LLM.
    Skeleton: returns empty list; extend with OpenAI/Anthropic API calls.
    """

    def __init__(self, api_key: str | None = None, model: str = "gpt-4") -> None:
        self.api_key = api_key
        self.model = model

    def analyze(self, text: str) -> list[str]:
        """
        Extract hidden assumptions from text.
        Stub: no API call; returns empty list.
        Future: call LLM with prompt like "Extract hidden assumptions in the following text..."
        """
        return []
