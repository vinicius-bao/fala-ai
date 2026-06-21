; Inno Setup - instalador do Assistente de Voz
; Compile com:  iscc installer.iss   (depois de gerar dist\AssistenteDeVoz\ com o PyInstaller)
; Download do Inno Setup: https://jrsoftware.org/isdl.php

#define AppName "Assistente de Voz"
#define AppVersion "0.1.0"
#define AppExe "AssistenteDeVoz.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-47A8-9B0C-1234567890AB}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Vinícius
DefaultDirName={autopf}\Assistente de Voz
DefaultGroupName=Assistente de Voz
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=AssistenteDeVoz-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Instala por usuário (sem exigir administrador)
PrivilegesRequired=lowest

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"
Name: "startup"; Description: "Iniciar o Assistente de Voz junto com o Windows"; GroupDescription: "Inicialização:"

[Files]
Source: "dist\AssistenteDeVoz\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Assistente de Voz"; Filename: "{app}\{#AppExe}"
Name: "{group}\Desinstalar Assistente de Voz"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Assistente de Voz"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "AssistenteDeVoz"; \
    ValueData: """{app}\{#AppExe}"""; Tasks: startup; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir o Assistente de Voz agora"; \
    Flags: nowait postinstall skipifsilent
