[Setup]
AppName=AudioCast
AppVersion=1.0
DefaultDirName={pf}\AudioCast
OutputDir=Output
OutputBaseFilename=AudioCast_Installer
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\client.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\server.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\AudioCast Client"; Filename: "{app}\client.exe"
Name: "{group}\AudioCast Server"; Filename: "{app}\server.exe"