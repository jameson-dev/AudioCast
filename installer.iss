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
SetupIconFile=assets\audiocast.ico
UninstallDisplayIcon=assets\audiocast.ico

[Files]
Source: "dist\client.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\server.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\audiocast.ico"; DestDir: "{app}\assets"

[Icons]
Name: "{group}\AudioCast Client"; Filename: "{app}\client.exe"; IconFilename: "{app}\assets\audiocast.ico"
Name: "{group}\AudioCast Server"; Filename: "{app}\server.exe"; IconFilename: "{app}\assets\audiocast.ico"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "AudioCast"; ValueData: "{app}\client.exe"; Flags: uninsdeletevalue