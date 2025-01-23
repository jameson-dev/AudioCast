# 🎧 RFAStream Streaming System
**RFAStream** is a client-server audio streaming system designed to broadcast audio alerts in real-time for RFAs (Request for Assistance). It is  based on the requirements for **emergency services** keeping track of the job type and priority.

The server monitors a folder for `.rfa` files, which trigger corresponding `.wav` audio files to be streamed to clients. Alerts can be categorized by priority (e.g., P1, P2, P3), with audio played based on the alert's priority.

---

## Components:

A **server** that handles audio streaming, folder monitoring, and alert prioritization.

A **client** GUI application that receives audio streams, displays a GUI for playback control, and supports muting.

---

## Features
- **Real-time audio streaming:** Broadcasts audio alerts in real-time to connected clients.


- **Automatic folder monitoring:** The server watches for .rfa files and triggers the corresponding .wav audio files.


- **Priority-based alerts:** Alerts can be categorized by priority (e.g., P1, P2, P3), and different audio files can be played sequentially depending on the priority level.


- **GUI-based client:** The client provides a user interface with tray icon support for easy control of playback.


- **Pause and resume broadcast functionality: Allows clients to pause or resume the audio broadcast.**


- **Individual client muting:** Clients can mute their audio independently via the GUI.


- **Automatic reconnect:** The client automatically reconnects to the server with a retry mechanism in case of disconnection.


- **Multi-threaded server:** Supports handling multiple clients simultaneously, ensuring efficient real-time streaming.

---

## How It Works
The RFAStream Server continuously monitors a specified folder for `.rfa` files. When a new `.rfa` file is created, the server matches it to the corresponding audio files based on the naming conventions (including priority). The audio files are then streamed to connected clients. Clients receive and play the audio based on the priority and other relevant conditions.