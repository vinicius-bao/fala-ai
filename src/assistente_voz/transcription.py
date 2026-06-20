"""Transcrição de áudio. Motor plugável; implementação padrão usa a Groq."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TranscriptionEngine(Protocol):
    def transcribe(self, wav_bytes: bytes, language: str = "pt") -> str: ...


class GroqEngine:
    """Whisper via API da Groq (https://console.groq.com)."""

    def __init__(self, api_key: str, model: str = "whisper-large-v3"):
        if not api_key:
            raise ValueError("GROQ_API_KEY ausente")
        from groq import Groq

        self._client = Groq(api_key=api_key)
        self._model = model

    def transcribe(self, wav_bytes: bytes, language: str = "pt") -> str:
        resp = self._client.audio.transcriptions.create(
            file=("audio.wav", wav_bytes),
            model=self._model,
            language=language,
            response_format="text",
        )
        # response_format="text" devolve uma string; defensivo de qualquer modo.
        text = resp if isinstance(resp, str) else getattr(resp, "text", str(resp))
        return text.strip()
