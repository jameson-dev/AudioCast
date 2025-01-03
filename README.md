
# 🎧 AudioCast Streaming System

**AudioCast** is a client-server audio streaming system designed to broadcast audio files detected in a specific folder. The server monitors a folder for `.rfa` files, matches them to corresponding `.wav` audio files, and streams them to connected clients in real-time.

This project includes:
- A **Server** that handles audio streaming and folder monitoring.
- A **Client** that receives audio streams and displays a GUI for controlling playback.




## Features

- Real-time audio streaming.
- Automatic folder monitoring for `.rfa` file creation.
- GUI-based client with tray icon support.
- Pause and resume broadcast functionality.
- Automatic reconnect with retry mechanism.
- Multi-threaded server supporting multiple clients.

---