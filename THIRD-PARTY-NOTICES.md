# Avisos de terceiros — Fala AI

O Fala AI é distribuído junto com bibliotecas de terceiros. Cada uma mantém sua
própria licença, que prevalece sobre a licença do Fala AI no que diz respeito
a esses componentes.

| Componente | Licença | Projeto |
|---|---|---|
| PySide6 / Qt for Python | **LGPL-3.0** | https://www.qt.io/qt-for-python |
| pynput | **LGPL-3.0** | https://github.com/moses-palmer/pynput |
| sounddevice | MIT | https://python-sounddevice.readthedocs.io |
| pyperclip | BSD-3-Clause | https://github.com/asweigart/pyperclip |
| NumPy | BSD-3-Clause | https://numpy.org |
| groq (SDK) | Apache-2.0 | https://github.com/groq/groq-python |
| openai (SDK) | Apache-2.0 | https://github.com/openai/openai-python |
| python-dotenv | BSD-3-Clause | https://github.com/theskumar/python-dotenv |
| platformdirs | MIT | https://github.com/tox-dev/platformdirs |
| PyInstaller (empacotamento) | GPL-2.0-or-later **com exceção** | https://pyinstaller.org |

## Sobre o PyInstaller

O PyInstaller é usado apenas para **empacotar** o aplicativo. Sua licença possui
uma exceção explícita que permite distribuir os executáveis gerados sob os
termos que o autor escolher — portanto ela não se estende ao Fala AI.

## Conformidade com a LGPL (Qt/PySide6 e pynput)

Estes componentes são usados sob a **LGPL-3.0**, sem modificações no código
original. Para atender às condições da licença:

1. **Vinculação dinâmica e substituição.** O Fala AI é distribuído em formato de
   **pasta** (não em arquivo único), com as bibliotecas em arquivos separados
   dentro do diretório de instalação. Assim, quem usa o programa pode
   **substituir essas bibliotecas** por outra versão compatível — basta trocar
   os arquivos correspondentes na pasta de instalação.
2. **Texto das licenças.** As licenças completas acompanham os respectivos
   pacotes, dentro da pasta de instalação (arquivos `LICENSE*` distribuídos
   junto às bibliotecas), e estão disponíveis publicamente:
   - LGPL-3.0: https://www.gnu.org/licenses/lgpl-3.0.html
   - GPL-3.0: https://www.gnu.org/licenses/gpl-3.0.html
3. **Código-fonte.** O código-fonte original dessas bibliotecas está disponível
   nos endereços indicados na tabela acima.

## Serviços externos

O aplicativo se comunica com APIs de terceiros (Groq, OpenAI e Google Gemini)
usando uma chave fornecida pelo próprio usuário. Esses serviços têm seus
próprios termos de uso e políticas de privacidade.
