"""Carrega uma pasta de documentação como texto de contexto (puro, testável)."""

from __future__ import annotations

from pathlib import Path

CONTEXT_EXTS = {".md", ".txt", ".markdown"}


def load_context(folder: str, max_chars: int = 12000) -> str:
    """Lê os arquivos de texto da pasta e devolve um bloco único de contexto.

    Limita o total a ``max_chars`` para não estourar o prompt.
    """
    if not folder:
        return ""
    root = Path(folder)
    if not root.is_dir():
        return ""
    parts: list[str] = []
    total = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in CONTEXT_EXTS:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").strip()
        except OSError:
            continue
        if not text:
            continue
        chunk = f"## {path.name}\n{text}\n"
        if total + len(chunk) > max_chars:
            chunk = chunk[: max(0, max_chars - total)]
        parts.append(chunk)
        total += len(chunk)
        if total >= max_chars:
            break
    return "\n".join(parts).strip()
