import os
import re
import socket
import threading
import pyaudio
import signal
from pathlib import Path
import argparse
from loguru import logger
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, DirCreatedEvent, FileCreatedEvent
from concurrent.futures import ThreadPoolExecutor

parser = argparse.ArgumentParser(description="AudioCast Streaming Server")
parser.add_argument("--host", default="0.0.0.0", help="Server Hostname (Default: 0.0.0.0)")
parser.add_argument("--port", type=int, default=12345, help="Server Port (Default: 12345)")
parser.add_argument("--watchdog-folder", default="rfa", help="Folder to monitor for .rfa files")
parser.add_argument("--audio-files", default="wav-files", help="Folder where .wav files are stored")

args = parser.parse_args()

# Folder to monitor
WATCHDOG_FOLDER = Path(args.watchdog_folder)
AUDIO_FILES_FOLDER = Path(args.audio_files)

# Server settings
HOST = args.host
PORT = args.port

# pyAudio settings
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

# pyAudio instance
p = pyaudio.PyAudio()

shutdown_event = threading.Event()


def check_dirs(dir_path):
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
            logger.info(f"Directory missing. Creating now: {dir_path}")
        except OSError as e:
            logger.error(f"Failed to create directory ({dir_path}): {e}")
    else:
        logger.info(f"Directory exists ({dir_path}). Continuing")


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

        # Extract the meaningful part of the filename (before the timestamp and ID)
        match = re.match(r"([a-zA-Z0-9_]+)_(\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2}Z)_.*", base_name)
        if not match:
            logger.error(f"Filename format is unrecognized: {base_name}")
            return

        keyword_part = match.group(1)  # Extract the part before the timestamp
        normalized_keyword = keyword_part.replace("_", " ").lower().strip()

        # Replace spaces with underscores for .wav file matching
        wav_file_name = normalized_keyword.replace(" ", "_") + ".wav"

        audio_file_path = os.path.join(AUDIO_FILES_FOLDER, wav_file_name)

        if os.path.exists(audio_file_path):
            logger.debug(f"Found audio file {audio_file_path}")
            logger.info(f"Streaming {audio_file_path}")
            self.stream_audio(audio_file_path)
        else:
            logger.error(f"Error: Audio file '{audio_file_path}' not found.")

    def stream_audio(self, file_path):
        try:
            with open(file_path, 'rb') as audio_file:
                while chunk := audio_file.read(CHUNK_SIZE):
                    # Send chunks of audio to all connected clients
                    self.server.broadcast_audio(chunk)
        except FileNotFoundError:
            logger.error(f"Audio file not found: {file_path}")


class AudioServer:
    def __init__(self, host, port, max_workers=10):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        self.clients = []

        # Initialise thread pool
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        self.observer = Observer()
        self.event_handler = FileHandler(self)
        self.observer.schedule(self.event_handler, WATCHDOG_FOLDER, recursive=False)

    def handle_client(self, client_socket, client_address):
        logger.info(f"New client connected: {client_address}")
        self.clients.append(client_socket)
        try:
            while True:
                # Keep connection alive
                client_socket.recv(1024) # Check for data/activity
                pass
        except (ConnectionRefusedError, BrokenPipeError):
            logger.warning(f"Client {client_address} disconnected unexpectedly")
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
        try:
            while not shutdown_event.is_set():
                # Non-blocking accept with timeout
                self.server_socket.settimeout(1.0)
                try:
                    client_socket, client_address = self.server_socket.accept()
                    self.executor.submit(self.handle_client, client_socket, client_address)
                except socket.timeout:
                    continue
        finally:
            self.shutdown()

    def shutdown(self):
        logger.info(f"Shutting down server...")
        shutdown_event.set()

        # Stop accepting new connections
        self.server_socket.close()

        # Stop all threads in the thread pool
        self.executor.shutdown(wait=True)

        # Stop folder monitoring
        self.observer.stop()
        self.observer.join()

        # Close all connected clients
        for client_socket in self.clients:
            client_socket.close()

        logger.info(f"Server shutdown complete.")

    def start_folder_monitor(self):
        self.observer.start()


def signal_handler(signum, frame):
    logger.info(f"Signal {signum} received. Initiating shutdown...")
    shutdown_event.set()


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    check_dirs(WATCHDOG_FOLDER)
    check_dirs(AUDIO_FILES_FOLDER)

    server = AudioServer(HOST, PORT)
    server.start_folder_monitor()

    try:
        server.start()
    except Exception as e:
        logger.error(f"Server encountered an error: {e}")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
