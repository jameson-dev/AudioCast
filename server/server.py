import os
import re
import socket
import threading
import time
import json

import pyaudio
import signal
from pathlib import Path
import argparse
from loguru import logger
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, DirCreatedEvent, FileCreatedEvent
from concurrent.futures import ThreadPoolExecutor


def load_config(config_path='server-config.json'):
    # Default config values
    default_config = {
        'host': '0.0.0.0',
        'port': 12345,
        'watchdog_folder': 'rfa',
        'audio_files': 'wav-files'
    }

    # Check if the config file exists
    if os.path.exists(config_path):
        # If the file exists, load it
        with open(config_path, 'r') as config_file:
            try:
                config = json.load(config_file)
                logger.info("Configuration loaded successfully.")
                return config
            except json.JSONDecodeError:
                logger.error("Invalid JSON format in config file. Using default settings.")
                return default_config
    else:
        # If the file does not exist, create it with default values
        with open(config_path, 'w') as config_file:
            json.dump(default_config, config_file, indent=4)
        logger.warning(f"Config file '{config_path}' not found. Creating it now..")
        return default_config


parser = argparse.ArgumentParser(description="AudioCast Streaming Server")
parser.add_argument("--host", default="0.0.0.0", help="Server Hostname (Default: 0.0.0.0)")
parser.add_argument("--port", type=int, default=12345, help="Server Port (Default: 12345)")
parser.add_argument("--watchdog-folder", default="rfa", help="Folder to monitor for .rfa files")
parser.add_argument("--audio-files", default="wav-files", help="Folder where .wav files are stored")

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
    def __init__(self, server, audio_files_folder):
        self.server = server
        self.audio_files_folder = audio_files_folder  # Store it as an instance variable

    def on_created(self, event: DirCreatedEvent | FileCreatedEvent) -> None:
        if event.is_directory:
            return
        if event.src_path.endswith(".rfa"):
            logger.info(f"New .rfa file detected: {event.src_path}")
            self.handle_rfa_file(event.src_path)

    def handle_rfa_file(self, rfa_file_path):
        base_name = os.path.splitext(os.path.basename(rfa_file_path))[0]

        # Extract the meaningful part of the filename (before the timestamp and ID)
        match = re.match(r"(P[1-3])_([a-zA-Z0-9_]+)_.*", base_name)
        if not match:
            logger.error(f"Filename format is unrecognized: {base_name}")
            return

        keyword_part = match.group(2)  # Extract the part after the priority
        normalized_keyword = keyword_part.replace("_", " ").lower().strip()

        # Check for Priority in filename:
        incident_priority = base_name[:2]   # Get P1, P2 or P3 from the start of the filename

        logger.info(f"Priority: {incident_priority}, Incident: {keyword_part}")

        # Replace spaces with underscores for .wav file matching
        inc_type_wav = normalized_keyword.replace(" ", "_") + ".wav"
        incident_priority_wav = f"{incident_priority}.wav"

        audio_file_path = os.path.join(self.audio_files_folder, inc_type_wav)
        inc_priority_audio_file_path = os.path.join(self.audio_files_folder, incident_priority_wav)

        if os.path.exists(audio_file_path) and os.path.exists(inc_priority_audio_file_path):
            logger.debug(f"Found audio file {audio_file_path}")
            logger.debug(f"Found priority audio file {inc_priority_audio_file_path}")
            logger.info(f"Streaming {inc_priority_audio_file_path} and {audio_file_path}")
            self.stream_audio_sequentially(audio_file_path, inc_priority_audio_file_path)
        # If priority wav file not found, just stream incident type wav
        elif os.path.exists(audio_file_path) and not os.path.exists(inc_priority_audio_file_path):
            logger.warning(f"Incident Priority ({inc_priority_audio_file_path}) could not be found. Only playing incident type ({audio_file_path})")
            self.stream_audio(audio_file_path)
        else:
            logger.error(f"Error: Audio file '{audio_file_path}' not found.")

    def stream_audio_sequentially(self, audio_file_path, priority_audio_path):
        """Stream two audio files sequentially to the client."""
        try:
            logger.info(f"Streaming audio files")

            # Send the incident priority audio file
            self.stream_audio(priority_audio_path)

            # Send the incident type audio file
            self.stream_audio(audio_file_path)



            logger.info("Both audio files streamed successfully.")
        except FileNotFoundError as e:
            logger.error("Error streaming audio: {e}")

    def stream_audio(self, file_path):
        try:
            with open(file_path, 'rb') as audio_file:
                while chunk := audio_file.read(CHUNK_SIZE):
                    # Send chunks of audio to all connected clients
                    self.server.broadcast_audio(chunk)
        except FileNotFoundError:
            logger.error(f"Audio file not found: {file_path}")


class AudioServer:
    def __init__(self, host, port, watchdog_folder, audio_files_folder, max_workers=10):
        self.host = host
        self.port = port
        self.watchdog_folder = Path(watchdog_folder)
        self.audio_files_folder = Path(audio_files_folder)  # Store audio_files_folder
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        self.clients = []
        self.client_status = {}
        self.broadcast_paused = False
        self.heartbeat_interval = 5

        # Initialize folder monitoring (watchdog)
        self.observer = Observer()
        self.event_handler = FileHandler(self, self.audio_files_folder)  # Pass AUDIO_FILES_FOLDER here
        self.observer.schedule(self.event_handler, self.watchdog_folder, recursive=False)

        # Initialize thread pool
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def handle_client(self, client_socket, client_address):
        logger.info(f"New client connected: {client_address}")
        self.clients.append(client_socket)

        # Send the current broadcast status (PAUSED/RESUMED) to the client on reconnect
        status_message = "PAUSED" if self.broadcast_paused else "RESUMED"
        client_socket.sendall(f"CONTROL:{status_message}".encode())

        try:
            while True:
                data = client_socket.recv(1024).decode().strip()
                if not data:
                    logger.warning(f"Client {client_address} disconnected due to no data.")
                    break

                if data == "PAUSE":
                    self.broadcast_paused = True
                    self.broadcast_control_message("PAUSED")
                    logger.info("Broadcast paused by a client.")
                elif data == "RESUME":
                    self.broadcast_paused = False
                    self.broadcast_control_message("RESUMED")
                    logger.info("Broadcast resumed by a client.")
                else:
                    logger.warning(f"Unknown command from client {client_address}: {data}")
        except Exception as e:
            logger.warning(f"Error handling client {client_address}: {e}")
        finally:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            client_socket.close()
            logger.info(f"Client {client_address} has been removed from the client list.")

    def broadcast_audio(self, chunk):
        for client_socket in self.clients:
            try:
                client_socket.sendall(chunk)
            except:
                self.clients.remove(client_socket)
                client_socket.close()

    def broadcast_control_message(self, message):
        control_message = f"CONTROL:{message}".encode()
        for client_socket in self.clients:
            try:
                client_socket.sendall(control_message)
            except:
                self.clients.remove(client_socket)
                client_socket.close()

    def start_heartbeat(self):
        while not shutdown_event.is_set():
            time.sleep(5)  # Heartbeat interval
            self.broadcast_control_message("HEARTBEAT")

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
    # Load configuration from config.json
    config = load_config()

    # Parse arguments
    args = parser.parse_args()

    # Override config values with command-line arguments if present
    config.update({
        'host': args.host or config['host'],
        'port': args.port or config['port'],
        'watchdog_folder': args.watchdog_folder or config['watchdog_folder'],
        'audio_files': args.audio_files or config['audio_files']
    })

    # Now use the values from config
    watchdog_folder = Path(config['watchdog_folder'])
    audio_files_folder = Path(config['audio_files'])
    host = config['host']
    port = config['port']

    # Check and create necessary directories
    check_dirs(watchdog_folder)
    check_dirs(audio_files_folder)

    # Start the server
    server = AudioServer(host, port, config['watchdog_folder'], config['audio_files'])
    server.start_folder_monitor()

    try:
        server.start()
    except Exception as e:
        logger.error(f"Server encountered an error: {e}")
    finally:
        server.shutdown()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)  # Handle Ctrl+C (SIGINT)
    signal.signal(signal.SIGTERM, signal_handler)  # Handle termination (SIGTERM)
    main()
