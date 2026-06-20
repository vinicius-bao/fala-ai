# Assistente de Voz

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

## Testes

A lógica pura (máquina de estados, histórico, parsing do atalho, config) tem
testes que rodam em qualquer sistema:

```powershell
python -m unittest discover -s tests -v
```

## Empacotar em .exe (opcional)

```powershell
pip install pyinstaller
pyinstaller --noconfirm --windowed --name AssistenteDeVoz src/assistente_voz/__main__.py
```

O executável fica em `dist/AssistenteDeVoz/`.

## Estrutura

```
src/assistente_voz/
  activation.py     # máquina de estados segurar/tocar (pura)
  audio.py          # gravação do microfone -> WAV
  transcription.py  # motor de STT plugável (Groq)
  hotkey.py         # atalho global + parsing
  output.py         # clipboard + colar (Ctrl+V)
  history.py        # histórico (memória + JSON)
  config.py         # configurações
  app.py            # controlador (orquestra tudo)
  ui.py             # bandeja + janela (abas Histórico/Configurações)
  __main__.py       # ponto de entrada
```

Documento de design: [`docs/superpowers/specs`](docs/superpowers/specs/).
