"""Contador de uso: quanto áudio já foi transcrito, por provedor.

Guardado à parte do config (é dado acumulado, não configuração). O custo é
apenas uma estimativa a partir de uma taxa que o usuário informa — preço de API
muda, então o app não finge saber o valor.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Stats:
    seconds: float = 0.0
    count: int = 0

    @property
    def minutes(self) -> float:
        return self.seconds / 60.0

    @property
    def hours(self) -> float:
        return self.seconds / 3600.0


def format_duration(seconds: float) -> str:
    """Segundos -> '2 h 05 min' / '7 min' / '45 s'."""
    seconds = max(0.0, seconds)
    if seconds < 60:
        return f"{int(seconds)} s"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes // 60} h {minutes % 60:02d} min"


class Usage:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else None
        self._by_provider: dict[str, Stats] = {}
        self.load()

    def add(self, provider: str, seconds: float = 0.0) -> None:
        stats = self._by_provider.setdefault(provider or "?", Stats())
        stats.count += 1
        if seconds and seconds > 0:
            stats.seconds += float(seconds)
        self.persist()

    def per_provider(self) -> dict[str, Stats]:
        return dict(self._by_provider)

    def total(self) -> Stats:
        return Stats(
            seconds=sum(s.seconds for s in self._by_provider.values()),
            count=sum(s.count for s in self._by_provider.values()),
        )

    def estimated_cost(self, rate_per_hour: float) -> float:
        if rate_per_hour <= 0:
            return 0.0
        return self.total().hours * rate_per_hour

    def reset(self) -> None:
        self._by_provider = {}
        self.persist()

    def load(self) -> None:
        if not (self.path and self.path.exists()):
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._by_provider = {
                str(k): Stats(
                    seconds=float(v.get("seconds", 0) or 0),
                    count=int(v.get("count", 0) or 0),
                )
                for k, v in data.items()
                if isinstance(v, dict)
            }
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            self._by_provider = {}

    def persist(self) -> None:
        if not self.path:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(
                    {
                        k: {"seconds": round(v.seconds, 2), "count": v.count}
                        for k, v in self._by_provider.items()
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except OSError:  # contador nunca pode derrubar o app
            pass
