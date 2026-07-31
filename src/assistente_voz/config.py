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

# Provedores de transcrição disponíveis.
PROVIDERS = ("groq", "openai", "gemini")
PROVIDER_LABELS = {
    "groq": "Groq (Whisper)",
    "openai": "OpenAI",
    "gemini": "Google Gemini",
}
DEFAULT_MODELS = {
    "groq": "whisper-large-v3",
    "openai": "gpt-4o-transcribe",
    "gemini": "gemini-2.0-flash",
}
# Modelos de CHAT (usados no refinamento).
DEFAULT_CHAT_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
}
_P_NATURAL = """Você revisa transcrições de fala em português do Brasil.
Devolva SOMENTE o texto revisado, sem título, aspas ou comentários.

Faça:
- Corrija português, concordância, acentuação e pontuação.
- Divida em PARÁGRAFOS curtos, um por assunto, separados por linha em branco.
- Remova vícios de fala e repetições que não acrescentam nada ("né", "tipo",
  "aí", "então", "no caso", "enfim", "assim", "olha"), quando forem só muleta.
- Corrija palavras que a transcrição claramente errou, deduzindo pelo contexto
  (termos técnicos, nomes próprios, nomes de ferramentas).
- Prefira frases diretas e curtas; evite ponto e vírgula e vírgulas em excesso.

Não faça:
- Não invente informações nem responda ao conteúdo.
- Não resuma nem mude o sentido; mantenha a primeira pessoa.
- Não adicione saudação, despedida ou observações."""

_P_PROMPT_IA = """Você transforma uma fala ditada em um prompt claro para uma IA.
Devolva SOMENTE o prompt final, sem preâmbulo nem comentários.

- Organize em parágrafos curtos; use lista com "-" quando houver vários itens.
- Deixe o pedido explícito e sem ambiguidade.
- Preserve TODOS os detalhes: termos técnicos, nomes de arquivos, caminhos,
  números e nomes próprios. Corrija os que a transcrição errou, pelo contexto.
- Remova vícios de fala, hesitações e repetições.
- Não invente requisitos e não responda ao pedido — apenas reescreva."""

_P_FORMAL = """Você revisa uma fala ditada e devolve um texto formal e objetivo
em português do Brasil. Devolva SOMENTE o texto.

- Registro profissional: sem gírias, vícios de fala ou marcas de oralidade.
- Parágrafos curtos, um por assunto, separados por linha em branco.
- Preserve todas as informações; não invente nada e não responda ao conteúdo."""

_P_PONTUACAO = """Você apenas formata uma transcrição de fala em português do
Brasil. Devolva SOMENTE o texto.

- Ajuste pontuação, acentuação e maiúsculas.
- Divida em parágrafos por assunto, separados por linha em branco.
- NÃO troque palavras, NÃO remova vícios de fala e NÃO reescreva frases."""

# Estilos de refino prontos (o usuário pode editar o prompt livremente).
REFINE_PRESETS = {
    "natural": ("Mensagem natural (recomendado)", _P_NATURAL),
    "prompt_ia": ("Prompt para IA", _P_PROMPT_IA),
    "formal": ("Texto formal", _P_FORMAL),
    "pontuacao": ("Só pontuação e parágrafos", _P_PONTUACAO),
}
DEFAULT_REFINE_PROMPT = _P_NATURAL
_PROVIDER_ENV = {
    "groq": ("GROQ_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
}


@dataclass
class Config:
    hotkey: str = "ctrl+alt+space"
    tap_threshold_ms: int = 400
    language: str = "pt"
    theme_mode: str = "auto"           # "auto" | "light" | "dark"
    output_mode: str = "paste"          # "paste" | "clipboard_only"
    restore_clipboard: bool = False     # restaurar clipboard anterior após colar
    history_size: int = 50
    autostart: bool = False
    provider: str = "groq"             # "groq" | "openai" | "gemini"
    groq_model: str = "whisper-large-v3"
    groq_api_key: str = ""              # vazio => usa GROQ_API_KEY do ambiente
    openai_model: str = "gpt-4o-transcribe"
    openai_api_key: str = ""           # vazio => usa OPENAI_API_KEY do ambiente
    gemini_model: str = "gemini-2.0-flash"
    gemini_api_key: str = ""           # vazio => usa GEMINI_API_KEY do ambiente
    refine_hotkey: str = "ctrl+alt+w"  # 2º atalho: transcreve e refina via LLM
    refiner_provider: str = "groq"
    refiner_model: str = "llama-3.3-70b-versatile"
    refine_prompt: str = DEFAULT_REFINE_PROMPT
    refine_preset: str = "natural"
    transcribe_hint: str = ""          # termos frequentes (melhora o reconhecimento)
    context_enabled: bool = False
    context_dir: str = ""              # pasta de documentação usada como contexto
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


def provider_key_field(cfg: Config, provider: str) -> str:
    return {
        "groq": cfg.groq_api_key,
        "openai": cfg.openai_api_key,
        "gemini": cfg.gemini_api_key,
    }.get(provider, "")


def provider_model(cfg: Config, provider: str) -> str:
    model = {
        "groq": cfg.groq_model,
        "openai": cfg.openai_model,
        "gemini": cfg.gemini_model,
    }.get(provider, "")
    return model.strip() or DEFAULT_MODELS.get(provider, "")


def resolve_provider_key(cfg: Config, provider: str) -> str:
    """Chave do provedor: variável de ambiente primeiro, depois a do config."""
    for env in _PROVIDER_ENV.get(provider, ()):
        value = os.environ.get(env, "").strip()
        if value:
            return value
    return provider_key_field(cfg, provider).strip()


def resolve_update_repo(cfg: Config) -> str:
    """Repositório de updates: override do config, senão o embutido no app."""
    return (cfg.update_repo or DEFAULT_UPDATE_REPO).strip()


def match_preset(prompt: str) -> str:
    """Descobre a qual estilo o prompt corresponde ('custom' se foi editado)."""
    prompt = (prompt or "").strip()
    for key, (_, text) in REFINE_PRESETS.items():
        if prompt == text.strip():
            return key
    return "custom"


def append_note(text: str, note: str) -> str:
    """Acrescenta um rótulo ao final do texto (se ambos forem não-vazios)."""
    text = text.strip()
    note = (note or "").strip()
    return f"{text}\n{note}" if text and note else text
