; Inno Setup - instalador do Fala AI
; Compile com:  iscc installer.iss   (depois de gerar dist\FalaAI\ com o PyInstaller)
; Download do Inno Setup: https://jrsoftware.org/isdl.php

#define AppName "Fala AI"
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#define AppExe "FalaAI.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-47A8-9B0C-1234567890AB}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Vinícius
DefaultDirName={autopf}\Fala AI
DefaultGroupName=Fala AI
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=FalaAI-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
; Detecta o Fala AI aberto e oferece fechá-lo antes de atualizar (evita
; arquivo em uso). O app cria esse mutex ao iniciar.
AppMutex=FalaAI-SingleInstance-Mutex
CloseApplications=yes
RestartApplications=no
; Usa o ícone só se você já gerou assets\icon.ico (veja assets/README.md).
#if FileExists("assets\icon.ico")
SetupIconFile=assets\icon.ico
#endif
UninstallDisplayIcon={app}\{#AppExe}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"
Name: "startup"; Description: "Iniciar o Fala AI junto com o Windows"; GroupDescription: "Inicialização:"

[Files]
Source: "dist\FalaAI\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; Licença do app e avisos de terceiros (exigido pela LGPL do Qt/pynput)
Source: "LICENSE"; DestDir: "{app}"; DestName: "LICENCA.txt"; Flags: ignoreversion
Source: "THIRD-PARTY-NOTICES.md"; DestDir: "{app}"; DestName: "AVISOS-DE-TERCEIROS.txt"; Flags: ignoreversion

[Icons]
Name: "{group}\Fala AI"; Filename: "{app}\{#AppExe}"
Name: "{group}\Desinstalar Fala AI"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Fala AI"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "FalaAI"; \
    ValueData: """{app}\{#AppExe}"""; Tasks: startup; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir o Fala AI agora"; \
    Flags: nowait postinstall skipifsilent
