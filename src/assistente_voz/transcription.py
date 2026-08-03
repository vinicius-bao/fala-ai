"""Transcrição de áudio. Motor plugável; implementação padrão usa a Groq."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TranscriptionEngine(Protocol):
    def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "pt",
        filename: str = "audio.wav",
        hint: str = "",
    ) -> str: ...


class GroqEngine:
    """Whisper via API da Groq (https://console.groq.com)."""

    def __init__(self, api_key: str, model: str = "whisper-large-v3"):
        if not api_key:
            raise ValueError("GROQ_API_KEY ausente")
        from groq import Groq

        self._client = Groq(api_key=api_key)
        self._model = model

    def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "pt",
        filename: str = "audio.wav",
        hint: str = "",
    ) -> str:
        # O nome do arquivo informa o formato à Groq (.opus/.ogg/.mp3/.wav...).
        # `prompt` enviesa o reconhecimento para os termos que costumo usar.
        extra = {"prompt": hint} if hint else {}
        resp = self._client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model=self._model,
            language=language,
            response_format="text",
            **extra,
        )
        # response_format="text" devolve uma string; defensivo de qualquer modo.
        text = resp if isinstance(resp, str) else getattr(resp, "text", str(resp))
        return text.strip()


class OpenAIEngine:
    """Transcrição via API da OpenAI (ex.: gpt-4o-transcribe, whisper-1)."""

    def __init__(self, api_key: str, model: str = "gpt-4o-transcribe"):
        if not api_key:
            raise ValueError("OPENAI_API_KEY ausente")
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "pt",
        filename: str = "audio.wav",
        hint: str = "",
    ) -> str:
        extra = {"prompt": hint} if hint else {}
        resp = self._client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model=self._model,
            language=language,
            response_format="text",
            **extra,
        )
        text = resp if isinstance(resp, str) else getattr(resp, "text", str(resp))
        return text.strip()


_GEMINI_MIME = {
    "wav": "audio/wav", "mp3": "audio/mp3", "ogg": "audio/ogg", "oga": "audio/ogg",
    "opus": "audio/ogg", "flac": "audio/flac", "aac": "audio/aac", "m4a": "audio/aac",
}


class GeminiEngine:
    """Transcrição via API do Google Gemini (generateContent, REST)."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        if not api_key:
            raise ValueError("GEMINI_API_KEY ausente")
        self._key = api_key
        self._model = model

    def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "pt",
        filename: str = "audio.wav",
        hint: str = "",
    ) -> str:
        import base64
        import json
        import urllib.request

        ext = filename.lower().rsplit(".", 1)[-1]
        mime = _GEMINI_MIME.get(ext, "audio/wav")
        extra_hint = (
            f" Termos que costumam aparecer: {hint}." if hint else ""
        )
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent?key={self._key}"
        )
        body = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": "Transcreva este áudio em texto, exatamente como "
                            "falado, sem adicionar nada além da transcrição."
                            + extra_hint,
                        },
                        {
                            "inline_data": {
                                "mime_type": mime,
                                "data": base64.b64encode(audio_bytes).decode("ascii"),
                            }
                        },
                    ]
                }
            ]
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()


class LocalWhisperEngine:
    """Whisper rodando na própria máquina (faster-whisper). Offline e sem custo.

    O modelo é baixado uma vez na primeira utilização e fica em cache.
    """

    INSTALL_HINT = (
        "O Whisper local precisa do pacote 'faster-whisper', que não vem junto "
        "com o instalador (são centenas de MB). Instale com "
        "'pip install faster-whisper' ou escolha outro provedor."
    )

    def __init__(self, api_key: str = "", model: str = "small"):
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise RuntimeError(self.INSTALL_HINT) from e
        # int8 na CPU é o melhor custo/benefício; com GPU o ctranslate2 usa CUDA
        self._model = WhisperModel(model or "small", device="auto",
                                   compute_type="int8")

    def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "pt",
        filename: str = "audio.wav",
        hint: str = "",
    ) -> str:
        import io

        segments, _info = self._model.transcribe(
            io.BytesIO(audio_bytes),
            language=language or None,
            initial_prompt=hint or None,
            vad_filter=True,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()


def make_engine(provider: str, api_key: str, model: str) -> TranscriptionEngine:
    """Cria o motor de transcrição do provedor escolhido."""
    if provider == "openai":
        return OpenAIEngine(api_key, model)
    if provider == "gemini":
        return GeminiEngine(api_key, model)
    if provider == "local":
        return LocalWhisperEngine(model=model)
    return GroqEngine(api_key, model)
