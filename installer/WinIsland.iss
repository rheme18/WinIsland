#define AppName "WinIsland"
#define AppVersion "0.9.7"
#define AppPublisher "WinIsland"
#define AppExeName "WinIsland.exe"

[Setup]
AppId={{6EA438E9-126B-4E32-96B3-FB21748A31E1}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\WinIsland
DefaultGroupName=WinIsland
UninstallDisplayIcon={app}\{#AppExeName}
SetupIconFile=..\assets\WinIsland.ico
WizardSmallImageFile=..\assets\WinIsland-icon.png
WizardImageFile=..\assets\WinIsland-setup-side.png
OutputDir=..\dist
OutputBaseFilename=WinIsland-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern dark hidebevels
WizardImageBackColor=#08090b
WizardSmallImageBackColor=#08090b
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
ShowLanguageDialog=yes
LanguageDetectionMethod=none
UsePreviousLanguage=no
DisableProgramGroupPage=yes
Uninstallable=yes
LicenseFile=..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"; InfoBeforeFile: "..\packaging\Welcome-en.txt"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"; InfoBeforeFile: "..\packaging\Welcome-tr.txt"

[CustomMessages]
english.LaunchNow=Launch WinIsland now
turkish.LaunchNow=WinIsland'ı şimdi çalıştır
english.DesktopShortcut=Create a desktop shortcut
turkish.DesktopShortcut=Masaüstü kısayolu oluştur
english.AdditionalShortcuts=Additional shortcuts:
turkish.AdditionalShortcuts=Ek kısayollar:

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopShortcut}"; GroupDescription: "{cm:AdditionalShortcuts}"; Flags: unchecked

[Files]
Source: "..\dist\WinIsland\*.*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{group}\WinIsland"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\WinIsland"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchNow}"; Flags: postinstall nowait skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigDir, ConfigPath, Lang: String;
begin
  if CurStep = ssPostInstall then
  begin
    if ActiveLanguage = 'turkish' then Lang := 'tr' else Lang := 'en';
    ConfigDir := ExpandConstant('{userappdata}\WinIsland');
    ForceDirectories(ConfigDir);
    ConfigPath := ConfigDir + '\config.json';
    if not FileExists(ConfigPath) then
      SaveStringToFile(ConfigPath, '{' + #13#10 + '  "language": "' + Lang + '"' + #13#10 + '}', False);
  end;
end;
