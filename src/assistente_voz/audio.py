"""Captura de microfone -> WAV 16 kHz mono (suficiente para o Whisper)."""

from __future__ import annotations

import io
import wave


class Recorder:
    def __init__(self, samplerate: int = 16000, channels: int = 1):
        self.samplerate = samplerate
        self.channels = channels
        self._frames: list[bytes] = []
        self._stream = None
        self.last_duration_s = 0.0

    @property
    def is_recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        import sounddevice as sd

        self._frames = []
        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype="int16",
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, indata, frames, time_info, status) -> None:
        # indata é um array int16; copiamos os bytes porque o buffer é reusado.
        self._frames.append(bytes(indata))

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
