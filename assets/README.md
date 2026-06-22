# Assets (ícone e logo)

O app carrega os arquivos desta pasta. A ordem de preferência é:

1. `logo.png` — se existir, é usado como logo/ícone (coloque aqui o seu).
2. `logo.svg` — vetor da marca (já incluso, gerado por padrão).
3. fallback desenhado em tempo de execução (caso nenhum exista).

## Para usar a SUA logo

1. Coloque o seu arquivo como **`assets/logo.png`** (recomendado: PNG quadrado,
   fundo transparente, 512×512 ou maior).
2. Para o ícone do executável/instalador, gere o **`assets/icon.ico`**:
   ```powershell
   pip install pillow
   python tools/make_icon.py
   ```
   (isso lê `assets/logo.png` e cria `assets/icon.ico` com vários tamanhos).

Sem `icon.ico`, o build ainda funciona — o `.exe` só fica com o ícone padrão.

## Cores da marca (Fala AI)

- Gradiente: `#BD619D` → `#B48BB9` → `#FBB03B`
- Tema claro: fundo `#E6E7E8` / branco, texto `#5A5C63`
- Tema escuro: base `#5A5C63`, texto branco

Essas cores ficam centralizadas em `src/assistente_voz/theme.py`.
