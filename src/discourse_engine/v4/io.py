"""Adapter interfaces for STT and diarization backends.

These adapters convert audio/video inputs into DialogueTurn objects without
tying the engine to a specific provider (Whisper, Google STT, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from discourse_engine.v4.models import Dialogue, DialogueTurn, SpeakerProfile


class STTAdapter(ABC):
    """Abstract interface for speech-to-text backends."""

    @abstractmethod
    def transcribe(self, audio_path: str) -> Iterable[DialogueTurn]:
        """
        Transcribe an audio/video file into DialogueTurn objects.

        Implementations are responsible for:
        - Running STT (and optionally diarization).
        - Filling speaker_id (or using a placeholder like "speaker_1").
        - Providing start/end times when available.
        """
        raise NotImplementedError


class DiarizationAdapter(ABC):
    """Optional adapter for standalone speaker diarization."""

    @abstractmethod
    def diarize(self, audio_path: str) -> Iterable[DialogueTurn]:
        """
        Perform diarization and return DialogueTurns with speaker_id and timing,
        but with text possibly empty or coming from a separate STT step.
        """
        raise NotImplementedError


def dialogue_from_stt(adapter: STTAdapter, audio_path: str) -> Dialogue:
    """
    Helper to build a Dialogue from an STTAdapter.

    This keeps higher-level code independent from any particular STT backend.
    """
    turns = list(adapter.transcribe(audio_path))
    profiles: dict[str, SpeakerProfile] = {}
    for t in turns:
        if t.speaker_id not in profiles:
            profiles[t.speaker_id] = SpeakerProfile(
                speaker_id=t.speaker_id,
                display_name=t.display_name,
                role=t.role,
            )
    # Normalize turn indices
    for idx, t in enumerate(turns):
        t.turn_index = idx
    return Dialogue(turns=turns, speaker_profiles=profiles)

