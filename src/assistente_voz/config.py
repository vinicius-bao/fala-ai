"""Configuração do app.

Os campos são editáveis pela interface (aba Configurações). O arquivo de config
fica no diretório de usuário do SO (nunca no repositório). A chave da Groq pode
vir da variável de ambiente ``GROQ_API_KEY`` (tem prioridade) ou do config.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

APP_NAME = "assistente-voz"

# Repositório de atualização embutido no app (o usuário final NÃO configura isto).
# Defina como "usuario/repositorio" do GitHub quando o repo existir. Vazio =
# verificação de atualização desligada.
DEFAULT_UPDATE_REPO = "vinicius-bao/fala-ai"

# Rótulo acrescentado ao final de toda transcrição.
AI_NOTE = "transcrito por IA (pode ocorrer alguma divergência na fala)"


@dataclass
class Config:
    hotkey: str = "ctrl+alt+space"
    tap_threshold_ms: int = 400
    language: str = "pt"
    output_mode: str = "paste"          # "paste" | "clipboard_only"
    restore_clipboard: bool = False     # restaurar clipboard anterior após colar
    history_size: int = 50
    autostart: bool = False
    groq_model: str = "whisper-large-v3"
    groq_api_key: str = ""              # vazio => usa GROQ_API_KEY do ambiente
    update_repo: str = ""              # ex.: "usuario/fala-ai" (GitHub Releases)
    check_updates_on_start: bool = True
    ai_note_enabled: bool = False     # acrescentar o rótulo de IA às transcrições
    ai_note_text: str = AI_NOTE       # texto do rótulo (personalizável)

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def to_dict(self) -> dict:
        return asdict(self)


def config_dir() -> Path:
    from platformdirs import user_config_dir

    d = Path(user_config_dir(APP_NAME, appauthor=False))
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return config_dir() / "config.json"


def load_config(path: Path | None = None) -> Config:
    path = path or config_path()
    if path.exists():
        try:
            return Config.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return Config()


def save_config(cfg: Config, path: Path | None = None) -> None:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(cfg.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )


def resolve_api_key(cfg: Config) -> str:
    """Resolve a chave da Groq: ambiente primeiro, depois config."""
    return os.environ.get("GROQ_API_KEY", "").strip() or cfg.groq_api_key.strip()


def resolve_update_repo(cfg: Config) -> str:
    """Repositório de updates: override do config, senão o embutido no app."""
    return (cfg.update_repo or DEFAULT_UPDATE_REPO).strip()


def append_note(text: str, note: str) -> str:
    """Acrescenta um rótulo ao final do texto (se ambos forem não-vazios)."""
    text = text.strip()
    note = (note or "").strip()
    return f"{text}\n{note}" if text and note else text
