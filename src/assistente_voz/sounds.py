"""Bipes curtos de início e fim de gravação.

Os tons são gerados na hora (WAV em memória) e tocados de forma assíncrona, sem
dependência extra. Fora do Windows, vira no-op silencioso.
"""

from __future__ import annotations

import io
import math
import struct
import sys
import wave

_RATE = 22050


def tone_wav(freq: float, ms: int, volume: float = 0.22) -> bytes:
    """Gera um WAV curto com fade in/out (sem o 'clique' das bordas)."""
    n = int(_RATE * ms / 1000)
    fade = max(1, n // 8)
    frames = bytearray()
    for i in range(n):
        env = 1.0
        if i < fade:
            env = i / fade
        elif i > n - fade:
            env = max(0.0, (n - i) / fade)
        value = math.sin(2 * math.pi * freq * i / _RATE) * volume * env
        frames += struct.pack("<h", int(max(-1.0, min(1.0, value)) * 32767))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_RATE)
        wf.writeframes(bytes(frames))
    return buf.getvalue()


def _play(data: bytes) -> None:
    if sys.platform != "win32":
        return
    try:
        import winsound

        winsound.PlaySound(data, winsound.SND_MEMORY | winsound.SND_ASYNC)
    except Exception:  # noqa: BLE001 — som nunca pode quebrar a gravação
        pass


_START = None
_STOP = None


def play_start() -> None:
    global _START
    if _START is None:
        _START = tone_wav(880, 70)
    _play(_START)


def play_stop() -> None:
    global _STOP
    if _STOP is None:
        _STOP = tone_wav(520, 90)
    _play(_STOP)
