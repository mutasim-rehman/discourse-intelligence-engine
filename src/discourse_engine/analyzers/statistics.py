"""Basic text statistics analyzer."""

from discourse_engine.utils.text_utils import count_words, count_sentences


class StatisticsAnalyzer:
    """Computes word and sentence counts."""

    def analyze(self, text: str) -> tuple[int, int]:
        """Return (word_count, sentence_count)."""
        return count_words(text), count_sentences(text)
