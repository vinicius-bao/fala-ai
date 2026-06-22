# Fala AI

Aplicativo de **ditado por voz** para Windows. Você pressiona um atalho global,
fala, e o texto transcrito é **colado onde o cursor estiver**, **copiado para a
área de transferência** e **salvo no histórico**. Transcrição via **Groq
(Whisper large-v3)** — rápida e barata, com ótima precisão em português.

- **Segurar** o atalho = push-to-talk (grava enquanto segura).
- **Toque rápido** = liga/desliga (toca para começar, toca de novo para parar).

> ⚠️ Feito para **Windows**. Em Linux/macOS roda parcialmente (a captura de
> atalho global e o "colar" dependem de permissões específicas do SO).

## Pré-requisitos

- **Python 3.10+** no Windows.
- Uma **chave da API da Groq**: crie em https://console.groq.com/keys.

## Instalação

```powershell
# na pasta do projeto
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## Configurar a chave da Groq

Escolha **uma** das opções:

1. **Arquivo `.env`** na raiz do projeto (recomendado para desenvolvimento):
   ```
   GROQ_API_KEY=gsk_sua_chave_aqui
   ```
   (o `.env` já está no `.gitignore`, então nunca vai pro git.)

2. **Variável de ambiente** `GROQ_API_KEY` no Windows.

3. Pela **interface**: aba *Configurações* → campo *Chave Groq* → *Salvar*.

A ordem de prioridade é: variável de ambiente → `.env` → valor salvo na interface.

## Executar

```powershell
python -m assistente_voz
```

O app abre uma janela e fica na **bandeja** (system tray). Feche a janela para
mandá-lo para a bandeja; clique no ícone para reabrir.

### Como usar

1. Coloque o cursor onde quer escrever (Word, navegador, chat…).
2. **Segure** `Ctrl+Alt+Espaço` (padrão), fale, e **solte** → o texto aparece.
   - Ou **toque rápido** para gravar contínuo; **toque de novo** para finalizar.
3. O texto também fica no clipboard e na aba *Histórico* (com botão de copiar).

O atalho e todas as opções são configuráveis na aba *Configurações* — o atalho
tem um capturador: clique em "Definir atalho" e pressione a combinação desejada.

### Transcrever um áudio (ex.: mensagem de voz do WhatsApp)

Além de ditar ao vivo, dá para transcrever arquivos de áudio que você já tem:

1. Salve/baixe o áudio (a mensagem de voz do WhatsApp, por exemplo).
2. **Arraste o arquivo para a janela** do app — ou use o botão *🎧 Transcrever
   arquivo de áudio…* na aba *Histórico* (ou o item no menu da bandeja).
3. A transcrição aparece **numa janela dentro do app** (com botão *Copiar*) e
   também entra no *Histórico*.

Formatos aceitos: `.opus`, `.ogg`, `.mp3`, `.m4a`, `.mp4`, `.wav`, `.webm`,
`.flac` (enviados direto à Groq, sem conversão). Limite ~25 MB — folgado para
mensagens de voz.

## Testes

A lógica pura (máquina de estados, histórico, parsing do atalho, config) tem
testes que rodam em qualquer sistema:

```powershell
python -m unittest discover -s tests -v
```

## Gerar o instalador (Setup.exe)

Para usar como um programa normal (duplo clique, atalho no Menu Iniciar,
desinstalador), gere um instalador. **Isso roda numa máquina Windows** — o
PyInstaller não compila a partir de outro sistema.

**Pré-requisitos da máquina de build:**
- Python 3.10+
- [Inno Setup](https://jrsoftware.org/isdl.php) (grátis) — para gerar o `Setup.exe`.

**Gerar tudo com um comando:**

```powershell
build.bat
```

O `build.bat` cria o ambiente, instala as dependências, roda o PyInstaller e o
Inno Setup. No fim você tem:

- `dist\FalaAI\` — o app já executável (pasta).
- `installer\FalaAI-Setup.exe` — **o instalador** para distribuir.

> Se o Inno Setup não estiver instalado, o `build.bat` ainda gera o executável em
> `dist\FalaAI\`; depois é só instalar o Inno Setup e rodar
> `iscc installer.iss`.

**Quem recebe o `Setup.exe`** só dá duplo clique, escolhe (opcional) atalho na
área de trabalho e iniciar com o Windows, e pronto — não precisa de Python.

> A chave da Groq não vai dentro do instalador. No primeiro uso, defina-a pela
> aba *Configurações* ou na variável de ambiente `GROQ_API_KEY`.

## Atualizações

O app pode verificar se há versão nova no **GitHub Releases**:

- O repositório fica **embutido no app** (`DEFAULT_UPDATE_REPO` em
  [`src/assistente_voz/config.py`](src/assistente_voz/config.py)) — o usuário
  final não configura nada. Defina-o como `usuario/repositorio` antes de gerar o
  `.exe`.
- O app checa ao abrir (e há *Verificar atualizações agora* nas Configurações e
  no menu da bandeja). Havendo versão nova, mostra as notas e um botão **Baixar
  e instalar** (baixa o `Setup.exe` e o executa).
- Para **publicar** uma atualização: suba a versão (em `installer.iss`,
  `pyproject.toml` e `src/assistente_voz/__init__.py`), gere o `Setup.exe` com o
  `build.bat` e crie um **Release** no GitHub com o `.exe` anexado.
- Configurações, histórico e a chave da Groq ficam fora da pasta de instalação,
  então **sobrevivem** às atualizações e reinstalações.

> Requer o projeto no GitHub com Releases. O build automático na nuvem
> (GitHub Actions) é o complemento natural — dá para configurar depois.

## Aparência (logo e cores)

- **Tema automático:** segue o claro/escuro do Windows.
- **Cores:** centralizadas em [`src/assistente_voz/theme.py`](src/assistente_voz/theme.py)
  (paletas `LIGHT`/`DARK` + gradiente da marca). Mudar o visual = editar lá.
- **Logo/ícone:** ficam em `assets/`. Já vem um `logo.svg` da marca; para usar a
  sua, coloque `assets/logo.png` e gere o `assets/icon.ico` (veja
  [`assets/README.md`](assets/README.md)).

## Estrutura

```
assets/             # logo.svg, logo.png (sua), icon.ico
src/assistente_voz/
  activation.py     # máquina de estados segurar/tocar (pura)
  audio.py          # gravação do microfone -> WAV
  audiofile.py      # leitura/validação de arquivos de áudio
  transcription.py  # motor de STT plugável (Groq)
  hotkey.py         # atalho global + parsing
  output.py         # clipboard + colar (Ctrl+V)
  history.py        # histórico (memória + JSON)
  config.py         # configurações
  resources.py      # carrega logo/ícone (com fallback)
  theme.py          # paleta de cores + estilo (QSS)
  app.py            # controlador (orquestra tudo)
  ui.py             # bandeja + janela (abas Histórico/Configurações)
  __main__.py       # ponto de entrada
```

Documento de design: [`docs/superpowers/specs`](docs/superpowers/specs/).
