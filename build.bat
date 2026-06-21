@echo off
setlocal
chcp 65001 >nul
echo ============================================================
echo   Assistente de Voz - gerar o instalador (Setup.exe)
echo ============================================================
echo.

REM --- 1. Ambiente virtual + dependencias ---
if not exist .venv (
    echo [1/3] Criando ambiente virtual...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
echo [1/3] Instalando dependencias...
python -m pip install --upgrade pip >nul
pip install -e . || goto :erro
pip install pyinstaller || goto :erro

REM --- 2. PyInstaller: gera dist\AssistenteDeVoz\ ---
echo.
echo [2/3] Gerando o executavel com PyInstaller...
pyinstaller --noconfirm AssistenteDeVoz.spec || goto :erro

REM --- 3. Inno Setup: gera installer\AssistenteDeVoz-Setup.exe ---
echo.
echo [3/3] Gerando o instalador com o Inno Setup...
where iscc >nul 2>nul
if errorlevel 1 (
    echo.
    echo [AVISO] Inno Setup ^(iscc^) nao encontrado no PATH.
    echo         O executavel ja esta pronto em: dist\AssistenteDeVoz\
    echo         Para gerar o instalador, instale o Inno Setup
    echo         ^(https://jrsoftware.org/isdl.php^) e rode:  iscc installer.iss
    goto :fim
)
iscc installer.iss || goto :erro

echo.
echo ============================================================
echo   PRONTO! Instalador em: installer\AssistenteDeVoz-Setup.exe
echo ============================================================
goto :fim

:erro
echo.
echo [ERRO] Algo falhou acima. Verifique as mensagens.
exit /b 1

:fim
endlocal
