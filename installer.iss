[Setup]
AppName=RFAStream
AppVerName=RFAStream
AppPublisher=Jameson Bell
AppVersion=1.0
DefaultDirName={pf}\RFAStream
DefaultGroupName=RFAStream
OutputDir=Output
OutputBaseFilename=RFAStream_Installer
Compression=lzma
SolidCompression=yes
Uninstallable=yes
SetupIconFile=assets\rfastream.ico
UninstallDisplayIcon=assets\rfastream.ico

[Types]
Name: "full"; Description: "Install both Client and Server"
Name: "client"; Description: "Install Client only"
Name: "server"; Description: "Install Server only"

[Components]
Name: "client"; Description: "Client"; Types: full client
Name: "server"; Description: "Server"; Types: full server

[Files]
; Include all client files and folders
Source: "dist\client\client.exe"; DestDir: "{app}\client"; Flags: recursesubdirs createallsubdirs ignoreversion; Components: client

; Include all server files and folders
Source: "dist\server\server.exe"; DestDir: "{app}\server"; Flags: recursesubdirs createallsubdirs ignoreversion; Components: server

; Include shared assets
Source: "assets\rfastream.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

; Add client-config.json to AppData folder
Source: "client\client-config.json"; DestDir: "{userappdata}\RFAStream"; Flags: ignoreversion

[Icons]
; Shortcut for client
Name: "{group}\RFAStream Client"; Filename: "{app}\client\client.exe"; IconFilename: "{app}\assets\rfastream.ico"; Components: client

; Shortcut for server
Name: "{group}\RFAStream Server"; Filename: "{app}\server\server.exe"; IconFilename: "{app}\assets\rfastream.ico"; Components: server

; Create a shortcut for the client-config.json in the installation folder
Name: "{app}\client\client-config.json"; Filename: "{userappdata}\RFAStream\client-config.json"; WorkingDir: "{app}"; IconFilename: "{app}\assets\rfastream.ico"

[Registry]
; Add client to startup only if client is installed
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "RFAStream"; ValueData: "{app}\client\client.exe"; Flags: uninsdeletevalue; Components: client

; Add icon to Uninstall
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\RFAStream"; ValueType: string; ValueName: "DisplayIcon"; ValueData: "{app}\assets\rfastream.ico"
