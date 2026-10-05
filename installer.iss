; Inno Setup script for Live Speech STT.
; Produces a single-click Windows installer wrapping the PyInstaller build in dist\LiveSpeechSTT.
; Requires: Inno Setup 6 (free) - https://jrsoftware.org/isdl.php
; Build with: build_installer.bat  (after running build.bat first)

#define MyAppName "Live Speech STT"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Live Speech STT"
#define MyAppExeName "LiveSpeechSTT.exe"

[Setup]
AppId={{B7E2B6B0-5B6B-4B8B-9D7B-7C1F6A5C9A11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=installer_output
OutputBaseFilename=LiveSpeechSTT-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
SetupIconFile=assets\icon.ico
WizardStyle=modern
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\LiveSpeechSTT\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
