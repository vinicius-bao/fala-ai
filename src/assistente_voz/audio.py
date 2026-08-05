"""Captura de microfone -> WAV 16 kHz mono (suficiente para o Whisper)."""

from __future__ import annotations

import io
import wave


def list_input_devices() -> list[str]:
    """Nomes dos microfones disponíveis (vazio se o áudio não estiver ok)."""
    try:
        import sounddevice as sd

        seen, names = set(), []
        for dev in sd.query_devices():
            name = (dev.get("name") or "").strip()
            if dev.get("max_input_channels", 0) > 0 and name and name not in seen:
                seen.add(name)
                names.append(name)
        return names
    except Exception:  # noqa: BLE001 — sem áudio disponível
        return []


def resolve_device(name: str):
    """Converte o nome do microfone em índice; None = padrão do sistema."""
    if not name:
        return None
    try:
        import sounddevice as sd

        for idx, dev in enumerate(sd.query_devices()):
            if dev.get("max_input_channels", 0) > 0 and dev.get("name") == name:
                return idx
    except Exception:  # noqa: BLE001
        pass
    return None  # sumiu (desconectado): cai no padrão


class Recorder:
    def __init__(self, samplerate: int = 16000, channels: int = 1, device: str = ""):
        self.samplerate = samplerate
        self.channels = channels
        self.device = device  # nome do microfone; "" = padrão do sistema
        self._frames: list[bytes] = []
        self._stream = None
        self.last_duration_s = 0.0
        self.level = 0.0  # nível atual do microfone (0..1), p/ a onda do pop-up
        self.peak_level = 0.0  # maior nível da gravação (detecta microfone mudo)

    @property
    def is_recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        import sounddevice as sd

        self._frames = []
        self.level = 0.0
        self.peak_level = 0.0
        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype="int16",
            device=resolve_device(self.device),
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, indata, frames, time_info, status) -> None:
        # indata é um array int16; copiamos os bytes porque o buffer é reusado.
        chunk = bytes(indata)
        self._frames.append(chunk)
        self.level = self._rms_level(chunk)
        if self.level > self.peak_level:
            self.peak_level = self.level

    @staticmethod
    def _rms_level(pcm: bytes) -> float:
        import array
        import math

        try:
            samples = array.array("h")
            samples.frombytes(pcm)
        except (ValueError, TypeError):
            return 0.0
        if not samples:
            return 0.0
        step = max(1, len(samples) // 512)  # subamostra p/ custo baixo
        subset = samples[::step]
        rms = math.sqrt(sum(v * v for v in subset) / len(subset))
        # Curva perceptual: fala normal precisa ocupar boa parte da onda, não
        # só 30% dela. O expoente < 1 levanta os níveis baixos.
        norm = (rms / 32768.0) * 10.0
        return max(0.0, min(1.0, norm**0.7))

    def stop(self) -> bytes:
        if self._stream is None:
            return b""
        self._stream.stop()
        self._stream.close()
        self._stream = None
        pcm = b"".join(self._frames)
        self._frames = []
        n_samples = len(pcm) // (2 * self.channels)
        self.last_duration_s = n_samples / float(self.samplerate)
        return self._to_wav(pcm)

    def _to_wav(self, pcm: bytes) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # int16
            wf.setframerate(self.samplerate)
            wf.writeframes(pcm)
        return buf.getvalue()
