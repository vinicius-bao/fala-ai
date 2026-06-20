"""Histórico de transcrições — memória + persistência em JSON."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Transcription:
    text: str
    timestamp: str          # ISO 8601
    duration_s: float
    engine: str

    @classmethod
    def create(cls, text: str, duration_s: float, engine: str) -> "Transcription":
        return cls(
            text=text,
            timestamp=datetime.now().isoformat(timespec="seconds"),
            duration_s=round(duration_s, 2),
            engine=engine,
        )


class History:
    def __init__(self, path: Path | None = None, max_size: int = 50):
        self.path = Path(path) if path else None
        self.max_size = max_size
        self._items: list[Transcription] = []
        self.load()

    def add(self, entry: Transcription) -> None:
        self._items.append(entry)
        if len(self._items) > self.max_size:
            self._items = self._items[-self.max_size :]
        self.persist()

    def recent(self, n: int = 50) -> list[Transcription]:
        """Mais recentes primeiro."""
        return list(reversed(self._items[-n:]))

    def all(self) -> list[Transcription]:
        return list(self._items)

    def clear(self) -> None:
        self._items = []
        self.persist()

    def load(self) -> None:
        if self.path and self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self._items = [Transcription(**d) for d in data][-self.max_size :]
            except (json.JSONDecodeError, OSError, TypeError):
                self._items = []

    def persist(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps([asdict(i) for i in self._items], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
