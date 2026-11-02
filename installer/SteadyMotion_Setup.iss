; ==============================================================================
; Script di Compilazione Inno Setup 6 per SteadyMotion AI Pro (MDR SaMD Classe I)
; Genera l'eseguibile unico: SteadyMotion_AI_Setup_v3.1.exe
; ==============================================================================

#define MyAppName "SteadyMotion AI Pro"
#define MyAppVersion "3.1"
#define MyAppPublisher "SteadyMotion Development Team"
#define MyAppURL "https://github.com/Ilponz/SteadyMotion-AI"
#define MyAppExeName "SteadyMotion-AI.exe"

[Setup]
AppId={{5A8D12F0-84E3-4B9F-83AA-7C64192938B1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\SteadyMotion AI
DisableProgramGroupPage=yes
LicenseFile=..\docs\medical_device_mdr\ISTRUZIONI_USO_IFU_CLASSE_I.md
PrivilegesRequired=admin
OutputDir=..\dist
OutputBaseFilename=SteadyMotion_AI_Setup_v3.1
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Copia tutti i file della distribuzione compilata PyInstaller
Source: "..\dist\SteadyMotion-AI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
; Configurazione automatica certificato Authenticode e registrazione Root per UI Access
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\Create_Local_Cert_And_Install.ps1"" -SourceDir ""{app}"" -TargetDir ""{app}"""; Flags: runhidden waituntilterminated; StatusMsg: "Configurazione certificati digitali e permessi UI Access..."
; Avvio facoltativo al termine dell'installazione
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
