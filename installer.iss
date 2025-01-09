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

[Types]
Name: "full"; Description: "Install both Client and Server"
Name: "client"; Description: "Install Client only"
Name: "server"; Description: "Install Server only"

[Components]
Name: "client"; Description: "Client"; Types: full client
Name: "server"; Description: "Server"; Types: full server

[Files]
; Include all client files and folders
Source: "dist\client\*"; DestDir: "{app}\client"; Flags: recursesubdirs createallsubdirs ignoreversion; Components: client

; Include all server files and folders
Source: "dist\server\*"; DestDir: "{app}\server"; Flags: recursesubdirs createallsubdirs ignoreversion; Components: server

; Include shared assets
Source: "assets\audiocast.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

[Icons]
; Shortcut for client
Name: "{group}\AudioCast Client"; Filename: "{app}\client\client.exe"; IconFilename: "{app}\assets\audiocast.ico"; Components: client

; Shortcut for server
Name: "{group}\AudioCast Server"; Filename: "{app}\server\server.exe"; IconFilename: "{app}\assets\audiocast.ico"; Components: server

[Registry]
; Add client to startup only if client is installed
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "AudioCast"; ValueData: "{app}\client\client.exe"; Flags: uninsdeletevalue; Components: client
