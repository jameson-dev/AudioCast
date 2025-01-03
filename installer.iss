[Setup]
AppName=AudioCast
AppVerName=AudioCast
AppPublisher=Jameson Bell
AppVersion=1.0
DefaultDirName={pf}\AudioCast
DefaultGroupName=AudioCast
OutputDir=Output
OutputBaseFilename=AudioCast_Installer
Compression=lzma
SolidCompression=yes
Uninstallable=yes

[Files]
Source: "dist\client.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\server.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\AudioCast Client"; Filename: "{app}\client.exe"
Name: "{group}\AudioCast Server"; Filename: "{app}\server.exe"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "AudioCast"; ValueData: "{app}\client.exe"; Flags: uninsdeletevalue