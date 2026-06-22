# Assistente de Voz — Ditado por Voz (MVP) — Documento de Design

- **Data:** 2026-06-20
- **Status:** Aprovado (desenho) — aguardando revisão final do spec
- **Autor:** Vinícius (com Claude)

## 1. Objetivo

Criar um aplicativo Windows, escrito em Python, que roda em segundo plano e
transforma fala em texto sob demanda. O usuário pressiona um atalho global, fala,
e o texto transcrito é colado onde o cursor estiver, copiado para a área de
transferência e registrado num histórico. O foco do MVP é **ditado rápido e
confiável** — substituir ferramentas pagas tipo Wispr Flow / Superwhisper para o
caso de uso de ditado.

## 2. Escopo

### Dentro do MVP
- App de bandeja (system tray) que inicia e roda em segundo plano.
- Atalho global configurável com **dupla ativação**:
  - **Segurar** o atalho = push-to-talk (grava enquanto segura, transcreve ao soltar).
  - **Toque rápido** = liga/desliga (toggle): toca para começar, toca de novo para parar.
- Gravação do microfone enquanto a ativação estiver ativa.
- Transcrição via **API Groq (Whisper large-v3)**, com português como idioma padrão.
- Entrega do texto: clipboard (sempre) → histórico (sempre) → colar no app ativo (se possível).
- Janela de **histórico** das últimas transcrições, com botão de copiar novamente.
- Janela/aba de **configurações** (atalho, limiar de toque, idioma, modo de saída, chave da API).
- Empacotamento em `.exe` via PyInstaller; opção de iniciar com o Windows.

### Fora do MVP (Fase 2+)
- **Modo comando** (segundo atalho) que envia a transcrição para o n8n e aciona ferramentas/agentes.
- Whisper **local** (o motor de STT já será plugável, mas só a implementação Groq entra no MVP).
- Comandos de formatação por voz, pontuação automática avançada, múltiplos perfis.
- Versões para macOS/Linux.

## 3. Requisitos funcionais

1. O app registra um atalho global que funciona mesmo sem foco na janela.
2. Ao pressionar o atalho, inicia gravação e mede a duração do pressionamento.
3. Ao soltar:
   - se a duração < `tap_threshold_ms` (padrão 400 ms) → trata como **toque** e entra em modo toggle (segue gravando até o próximo toque);
   - se ≥ `tap_threshold_ms` → trata como **push-to-talk** e encerra a gravação ao soltar.
4. Ao encerrar a gravação, o áudio é enviado para transcrição.
5. O texto transcrito é, nesta ordem: (a) escrito na área de transferência, (b) adicionado ao histórico, (c) colado no app em foco via Ctrl+V (se a janela aceitar).
6. O clipboard anterior do usuário é preservado e restaurado após o colar.
7. O histórico persiste em disco e sobrevive a reinícios do app.
8. O ícone da bandeja reflete o estado atual (ocioso / gravando / transcrevendo).

## 4. Requisitos não-funcionais

- **Latência:** do fim da fala até o texto aparecer, alvo de ~1–3 s para frases curtas (depende da rede e da Groq).
- **Privacidade:** o áudio é enviado para a Groq (nuvem). Isso é uma decisão consciente do MVP; o desenho plugável permite trocar por Whisper local depois.
- **Segurança:** a chave da API nunca fica no código. Vem de variável de ambiente `GROQ_API_KEY` ou de um arquivo de config no diretório de usuário; `.env` e configs ficam no `.gitignore`.
- **Robustez:** falhas de rede/API não podem perder o áudio nem travar o app.

## 5. Arquitetura e componentes

Cada módulo tem uma responsabilidade única, interface explícita e pode ser
testado isoladamente.

| Módulo | Responsabilidade | Dependência principal |
|---|---|---|
| `hotkey.py` | Escuta o atalho global; emite eventos `on_press` e `on_release(duration_s)` | `pynput` |
| `audio.py` | Grava o microfone; `start()` / `stop() -> bytes` (WAV 16 kHz mono) | `sounddevice` |
| `transcription.py` | Interface `TranscriptionEngine` + implementação `GroqEngine` (plugável) | `groq` / `httpx` |
| `output.py` | Escreve no clipboard e cola no app ativo (Ctrl+V), restaurando o clipboard | `pyperclip` + `pynput` |
| `history.py` | Armazena transcrições em memória e persiste em JSON | stdlib |
| `config.py` | Carrega/salva configurações; resolve a chave da API | stdlib + `platformdirs` |
| `ui.py` | Ícone na bandeja + janelas de histórico e configurações | `PySide6` |
| `app.py` | Orquestra tudo: a máquina de estados do ditado | — |
| `main.py` | Ponto de entrada | — |

### Contratos (esboço)

```python
# transcription.py
class TranscriptionEngine(Protocol):
    def transcribe(self, wav_bytes: bytes, language: str = "pt") -> str: ...

class GroqEngine:
    def __init__(self, api_key: str, model: str = "whisper-large-v3") -> None: ...
    def transcribe(self, wav_bytes: bytes, language: str = "pt") -> str: ...

# audio.py
class Recorder:
    def start(self) -> None: ...
    def stop(self) -> bytes: ...        # WAV 16 kHz mono
    @property
    def is_recording(self) -> bool: ...

# output.py
class TextOutput:
    def to_clipboard(self, text: str) -> None: ...
    def paste_into_active(self, text: str) -> bool: ...   # True se conseguiu colar

# history.py
@dataclass
class Transcription:
    text: str
    timestamp: datetime
    duration_s: float
    engine: str

class History:
    def add(self, entry: Transcription) -> None: ...
    def recent(self, n: int = 50) -> list[Transcription]: ...
```

O `app.py` é o único que conhece todos os módulos; os demais não dependem uns dos
outros, o que mantém as fronteiras limpas e facilita os testes.

## 6. Máquina de estados

```
Ocioso ──(início de gravação)──> Gravando ──(fim)──> Transcrevendo ──> Entregando ──> Ocioso
```

- **Ocioso:** aguardando o atalho. Ícone neutro.
- **Gravando:** capturando áudio. Ícone "ao vivo". Em modo toggle, permanece aqui entre os toques.
- **Transcrevendo:** áudio enviado à Groq; aguardando resposta. Ícone "processando".
- **Entregando:** aplica clipboard → histórico → colar. Volta a Ocioso.

Erros em qualquer estado retornam a Ocioso com notificação e preservação do áudio.

## 7. Lógica de ativação (dupla)

O `hotkey.py` apenas reporta press/release com a duração. A semântica fica no `app.py`:

- **Press** (estado Ocioso): inicia gravação, marca `t0`.
- **Release**:
  - `dur < tap_threshold_ms` → era um toque. Se estava em push-to-talk implícito,
    converte para **toggle** e continua gravando.
  - `dur >= tap_threshold_ms` → push-to-talk: encerra e transcreve.
- **Press** seguinte (estado Gravando via toggle): encerra a gravação e transcreve.

`tap_threshold_ms` é configurável (padrão 400 ms).

## 8. Saída e fallback

Ordem fixa e sempre executada: **clipboard → histórico → colar no cursor**.

- Colar usa Ctrl+V (mais rápido e lida melhor com acentuação que digitar tecla a tecla).
- O conteúdo anterior do clipboard é salvo e restaurado após um pequeno atraso.
- Se o colar falhar (app não aceita texto, sem janela em foco), o texto permanece
  garantido no clipboard e no histórico — **nada se perde**.
- Modo de saída configurável: `paste` (padrão) ou `clipboard_only`.

## 9. Transcrição

- Provedor: **Groq**, modelo `whisper-large-v3`.
- Idioma padrão: `pt` (configurável).
- Áudio enviado como WAV 16 kHz mono (suficiente para Whisper, payload menor).
- A interface `TranscriptionEngine` isola o provedor; trocar para Whisper local
  no futuro é só adicionar uma nova implementação.

## 10. Configuração

Campos:

| Campo | Padrão | Descrição |
|---|---|---|
| `hotkey` | `Ctrl+Alt+Espaço` | Atalho global de ditado (definido pelo capturador na aba Configurações) |
| `tap_threshold_ms` | 400 | Limiar toque × segurar |
| `language` | `pt` | Idioma da transcrição |
| `output_mode` | `paste` | `paste` ou `clipboard_only` |
| `history_size` | 50 | Quantidade de itens guardados |
| `autostart` | false | Iniciar com o Windows |
| `groq_api_key` | — | Lido de `GROQ_API_KEY` ou do arquivo de config |

Armazenado em JSON no diretório de config do usuário (`platformdirs`). A chave da
API tem prioridade pela variável de ambiente.

## 11. Interface (PySide6)

Uma **única janela** com abas reúne histórico e configurações — o usuário não
edita arquivo de config na mão.

- **Ícone de bandeja** com menu: abrir a janela, sair. Estado visual por
  cor/ícone (ocioso / gravando / transcrevendo).
- **Aba "Histórico":** lista das transcrições recentes (texto, horário), botão
  de copiar por item.
- **Aba "Configurações":** edição de todos os campos da seção 10 direto pela
  interface. Inclui um **capturador de atalho**: o usuário clica em "Definir
  atalho" e pressiona a combinação desejada, que é gravada e passa a valer na
  hora (sem reiniciar o app). Também edita limiar de toque, idioma, modo de
  saída, tamanho do histórico, autostart e a chave da Groq.
- As alterações são salvas no arquivo de config e aplicadas imediatamente (o
  listener de atalho é re-registrado ao mudar o atalho).
- Alternativa descartada: `pystray` + Tkinter (mais leve, porém UI inferior).

## 12. Tratamento de erros

- **Sem internet / erro da API:** notificação no painel; o áudio é guardado em
  disco para reenvio manual.
- **Microfone indisponível / sem permissão:** aviso claro; volta a Ocioso.
- **Gravação vazia / só silêncio:** ignora, sem chamar a API.
- **Falha ao colar:** silenciosa para o usuário (texto já está no clipboard + histórico).

## 13. Empacotamento e distribuição

- `.exe` único via **PyInstaller**.
- Opção de autostart (pasta Startup ou chave Run do registro).
- Documentar como obter a chave da Groq e configurá-la no primeiro uso.

## 14. Stack e dependências

- Python 3.11+
- `pynput`, `sounddevice`, `numpy`, `pyperclip`, `PySide6`, `platformdirs`
- `groq` (ou `httpx` direto na API)
- Dev/empacotamento: `pytest`, `pyinstaller`

## 15. Critérios de aceitação (verificáveis)

1. Segurar o atalho, falar "olá mundo" e soltar → "olá mundo" aparece no app em
   foco, no clipboard e no histórico, em poucos segundos.
2. Toque rápido inicia gravação contínua; um novo toque encerra e transcreve.
3. Com o cursor num alvo que não aceita texto (ex.: área de trabalho), o texto
   ainda aparece no clipboard e no histórico.
4. Sem internet, o painel mostra erro e o áudio fica salvo para reenvio.
5. A chave da API não aparece em nenhum arquivo versionado.
6. Alterar o atalho pela aba Configurações passa a valer sem reiniciar o app.

## 16. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| `pynput` exigir permissões/admin para hook global | Validar cedo; documentar; avaliar `keyboard` como alternativa |
| Latência alta da rede degradar a experiência | Áudio 16 kHz mono; feedback visual; Fase 2 com Whisper local |
| Restaurar clipboard com timing errado | Atraso configurável + testes |
| Conflito do atalho com outros apps | Atalho configurável |

## 17. Estrutura de arquivos (proposta)

```
assistente-de-voz/
  src/assistente_voz/
    __init__.py
    main.py
    app.py
    hotkey.py
    audio.py
    transcription.py
    output.py
    history.py
    config.py
    ui.py
  tests/
  docs/superpowers/specs/
  pyproject.toml
  README.md
  .gitignore
```

## 18. Adendo — Transcrição de arquivos de áudio (drag-and-drop)

Além do ditado ao vivo, o app transcreve arquivos de áudio já existentes,
principalmente **mensagens de voz do WhatsApp**.

- **Entrada:** arrastar-e-soltar o arquivo na janela, botão "Transcrever arquivo
  de áudio…" na aba Histórico, ou item equivalente no menu da bandeja.
- **Formatos:** `.opus`, `.ogg`, `.oga`, `.mp3`, `.m4a`, `.mp4`, `.wav`,
  `.webm`, `.flac`, `.mpeg`, `.mpga` — enviados direto à Groq, **sem conversão**
  (não precisa de ffmpeg). Limite ~25 MB.
- **Resultado:** mostrado **dentro do app** (janela com o texto + botão Copiar) e
  adicionado ao histórico. **Não cola** automaticamente nem sobrescreve o
  clipboard (a cópia é manual, pelo botão).
- **Módulo novo:** `audiofile.py` (validação de formato/tamanho e leitura), puro
  e testado. O motor de transcrição ganhou o parâmetro `filename` para a Groq
  detectar o formato. O fluxo de ditado por voz permanece inalterado.

## 19. Adendo — Verificação de atualização

- Módulo `updater.py`: parte pura (`parse_version`/`is_newer`, testada) + acesso
  ao GitHub Releases API (stdlib `urllib`).
- Repositório **embutido no app** (`DEFAULT_UPDATE_REPO` em `config.py`); o
  usuário final não configura. `config.update_repo` existe só como override
  avançado. `check_updates_on_start` liga a checagem ao iniciar.
- Fluxo: checa ao iniciar (se configurado) e manualmente (aba Configurações e
  menu da bandeja). Havendo versão nova, abre um diálogo com as notas e o botão
  "Baixar e instalar" (baixa o `Setup.exe` para a pasta temporária e o executa,
  encerrando o app). Há também "Abrir página" do release.
- Como configurações/histórico/chave ficam em AppData (fora da instalação), eles
  sobrevivem às atualizações. Requer o projeto no GitHub com Releases.

## 20. Adendo — Aviso de transcrição por IA (opcional)

- Opção em Configurações: `ai_note_enabled` (liga/desliga) e `ai_note_text`
  (texto personalizável; padrão em `AI_NOTE`). Quando ligado, o rótulo é
  acrescentado ao final de toda transcrição (ditado e arquivo), via
  `append_note` (puro, testado). Desligado por padrão.
