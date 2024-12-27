import os
import socket
import threading
import pyaudio
from loguru import logger
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, DirCreatedEvent, FileCreatedEvent

# Folder to monitor
WATCHDOG_FOLDER = './rfa'
AUDIO_FILES_FOLDER = './wav_files'

# Server settings
HOST = '0.0.0.0'
PORT = 12345

# pyAudio settings
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

# pyAudio instance
p = pyaudio.PyAudio()


class FileHandler(FileSystemEventHandler):
    def __init__(self, server):
        self.server = server

    def on_created(self, event: DirCreatedEvent | FileCreatedEvent) -> None:
        if event.is_directory:
            return
        if event.src_path.endswith(".rfa"):
            logger.info(f"New .rfa file detected: {event.src_path}")
            self.handle_rfa_file(event.src_path)

    def handle_rfa_file(self, rfa_file_path):
        base_name = os.path.splitext(os.path.basename(rfa_file_path))[0]
        audio_file_path = os.path.join(AUDIO_FILES_FOLDER, f"{base_name}.wav")

        if os.path.exists(audio_file_path):
            logger.debug(f"Found audio file {audio_file_path}")
            logger.info(f"Streaming {audio_file_path}")
            self.stream_audio(audio_file_path)
        else:
            logger.error(f"Error: Audio file '{audio_file_path}' not found.")

    def stream_audio(self, file_path):
        with open(file_path, 'rb') as audio_file:
            while chunk := audio_file.read(CHUNK_SIZE):
                # Send chunks of audio to all connected clients
                self.server.broadcast_audio(chunk)


class AudioServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        self.clients = []

        self.observer = Observer()
        self.event_handler = FileHandler(self)
        self.observer.schedule(self.event_handler, WATCHDOG_FOLDER, recursive=False)

    def handle_client(self, client_socket, client_address):
        logger.info(f"New client connected: {client_address}")
        self.clients.append(client_socket)
        try:
            while True:
                # Keep connection alive
                pass
        except:
            logger.info(f"Client {client_address} disconnected")
            self.clients.remove(client_socket)
            client_socket.close()

    def broadcast_audio(self, chunk):
        for client_socket in self.clients:
            try:
                client_socket.sendall(chunk)
            except:
                self.clients.remove(client_socket)
                client_socket.close()

    def start(self):
        logger.info(f"Server listening on {self.host}:{self.port}")
        while True:
            client_socket, client_address = self.server_socket.accept()
            threading.Thread(target=self.handle_client, args=(client_socket, client_address)).start()

    def start_folder_monitor(self):
        self.observer.start()


def main():
    server = AudioServer(HOST, PORT)
    server.start_folder_monitor()
    server.start()


if __name__ == "__main__":
    main()
