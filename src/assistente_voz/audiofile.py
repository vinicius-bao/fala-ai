"""Validação e leitura de arquivos de áudio para transcrição (puro, testável).

Formatos aceitos pela API da Groq — enviados sem conversão (não precisa ffmpeg).
"""

from __future__ import annotations

from pathlib import Path

SUPPORTED_EXTS = {
    ".opus", ".ogg", ".oga", ".mp3", ".m4a", ".mp4",
    ".wav", ".webm", ".flac", ".mpeg", ".mpga",
}
MAX_BYTES = 25 * 1024 * 1024  # limite prático da API da Groq


class AudioFileError(Exception):
    pass


def is_supported(path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTS


def read_audio(path) -> tuple[bytes, str]:
    """Valida e lê o arquivo. Retorna (bytes, nome). Levanta AudioFileError."""
    p = Path(path)
    if not p.is_file():
        raise AudioFileError(f"Arquivo não encontrado: {p}")
    if not is_supported(p):
        ext = p.suffix or "(sem extensão)"
        raise AudioFileError(
            f"Formato não suportado: {ext}.\n"
            f"Use um destes: {', '.join(sorted(SUPPORTED_EXTS))}"
        )
    size = p.stat().st_size
    if size == 0:
        raise AudioFileError("Arquivo de áudio vazio.")
    if size > MAX_BYTES:
        mb = size / (1024 * 1024)
        raise AudioFileError(
            f"Arquivo muito grande ({mb:.1f} MB). O limite é ~25 MB."
        )
    return p.read_bytes(), p.name
