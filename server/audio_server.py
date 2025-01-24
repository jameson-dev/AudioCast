import time
import socket
import threading
from pathlib import Path
from loguru import logger
from watchdog.observers import Observer
from concurrent.futures import ThreadPoolExecutor
from watchdog_monitor import FileHandler

shutdown_event = threading.Event()


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
