import socket
import threading
import time
import pyaudio
import argparse
from loguru import logger
from tkinter import Tk, Button, Label, StringVar
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw


parser = argparse.ArgumentParser(description="AudioCast Streaming Client")
parser.add_argument("--host", default='127.0.0.1', help="Server Hostname (Default: 127.0.0.1)")
parser.add_argument("--port", type=int, default=12345, help="Server Port (Default: 12345)")
parser.add_argument("--retry", type=int, default=5, help="Reconnect delay in seconds (Default: 5 seconds)")
parser.add_argument("--heartbeat", type=bool, default=True, help="Enable client heartbeat (Default: True)")
args = parser.parse_args()

# Server settings
HOST = args.host
PORT = args.port
RETRY_DELAY = args.retry
HEARTBEAT_ENABLED = args.heartbeat

# PyAudio settings
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

paused_event = threading.Event()
shutdown_event = threading.Event()

# PyAudio Instance
p = pyaudio.PyAudio()


class AudioCastClient:
    def __init__(self, host, port, retry_delay, heartbeat_enabled):
        self.host = host
        self.port = port
        self.retry_delay = retry_delay
        self.heartbeat_enabled = heartbeat_enabled

        self.client_socket = None

        self.shutdown_event = shutdown_event
        self.paused_event = paused_event
        self.connection_status = None  # Initialize as None, will be set in create_gui()

        self.socket_lock = threading.Lock()

    def connect_to_server(self):
        while not self.shutdown_event.is_set():
            try:
                logger.debug(f"Thread {threading.current_thread().name} waiting for socket lock...")
                if self.socket_lock.acquire(timeout=5):  # Timeout for acquiring lock
                    try:
                        logger.debug(f"Thread {threading.current_thread().name} acquired socket lock.")

                        if self.client_socket:
                            logger.debug("Closing existing socket before reconnecting.")
                            self.client_socket.close()
                            self.client_socket = None

                        logger.debug("Creating a new socket...")
                        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        client_socket.settimeout(5)
                        logger.debug(f"Connecting to {self.host}:{self.port}...")

                        client_socket.connect((self.host, self.port))

                        # If successful
                        self.client_socket = client_socket
                        logger.info(f"Connected to {self.host}:{self.port}")
                        self.connection_status.set("Connected")
                        return client_socket

                    finally:
                        self.socket_lock.release()
                        logger.debug(f"Thread {threading.current_thread().name} released socket lock.")
                else:
                    logger.warning("Failed to acquire socket lock within timeout.")
            except (socket.error, OSError) as e:
                logger.error(f"Error in connect_to_server: {e}")
                self.connection_status.set("Disconnected")
                time.sleep(self.retry_delay)

        logger.debug("Exiting connect_to_server due to shutdown event.")
        return None

    def stream_audio(self):
        logger.debug("stream_audio called")
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        output=True,
                        frames_per_buffer=CHUNK_SIZE)

        client_socket = None

        while not shutdown_event.is_set():
            if not client_socket:
                try:
                    client_socket = self.connect_to_server()
                    if client_socket:
                        self.connection_status.set("Connected")
                    else:
                        self.connection_status.set("Disconnected")
                        time.sleep(self.retry_delay)
                        continue
                except Exception as e:
                    logger.error(f"Failed to connect: {e}")
                    self.connection_status.set("Disconnected")
                    time.sleep(self.retry_delay)
                    continue

            try:
                data = client_socket.recv(CHUNK_SIZE)

                if not data:
                    logger.warning("No data received. Server may have disconnected.")
                    self.connection_status.set("Disconnected")
                    client_socket.close()
                    client_socket = None
                    continue

                # Check for control messages
                if data.startswith(b"CONTROL:"):
                    control_message = data.decode().split(":", 1)[1]
                    if control_message == "PAUSED":
                        logger.info("Broadcast is paused by the server.")
                        self.connection_status.set("Connected | Paused")
                        self.update_pause_button("Resume broadcasts")
                        paused_event.set()
                    elif control_message == "RESUMED":
                        logger.info("Broadcast is resumed by the server.")
                        self.connection_status.set("Connected | Broadcasting")
                        self.update_pause_button("Pause broadcasts")
                        paused_event.clear()
                    continue

                # Skip playback if paused
                if paused_event.is_set():
                    continue

                # Write audio data to stream
                stream.write(data)

            except socket.timeout:
                logger.debug("An expected socket timeout occurred; likely no data received sent to server")
                continue
            except socket.error as e:
                logger.error(f"Socket error: {e}")
                if client_socket:
                    client_socket.close()
                client_socket = None
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                if client_socket:
                    client_socket.close()
                client_socket = None

        stream.stop_stream()
        stream.close()
        if client_socket:
            client_socket.close()

    def create_tray_icon(self, root):
        def on_quit():
            shutdown_event.set()
            tray_icon.stop()

        def open_gui():
            root.deiconify()

        # Create tray icon
        image = Image.new('RGB', (64, 64), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 48, 48), fill=(255, 255, 255))

        menu = Menu(MenuItem('Open', open_gui), MenuItem('Quit', on_quit))

        tray_icon = Icon("AudioCast Client", image, "AudioCast", menu)

        return tray_icon

    def create_gui(self):
        root = Tk()
        root.title("AudioCast Client")
        root.geometry("300x200")

        self.connection_status = StringVar()
        self.connection_status.set("Disconnected")

        status_label = Label(root, textvariable=self.connection_status, font=("Arial", 12), fg="green")
        status_label.pack(pady=10)

        title_label = Label(root, text="AudioCast Client", font=("Arial", 16))
        title_label.pack(pady=10)

        self.pause_button = Button(root, text="Pause Notifications", command=self.toggle_pause)
        self.pause_button.pack(pady=5)

        exit_button = Button(root, text="Close to tray", command=root.withdraw)
        exit_button.pack(pady=5)

        root.withdraw()
        return root

    def toggle_pause(self):
        if self.client_socket:
            try:
                if paused_event.is_set():
                    # Send RESUME command to server
                    self.client_socket.sendall(b"RESUME")
                    paused_event.clear()
                    self.pause_button.config(text="Pause broadcasts")
                else:
                    # Send PAUSE command to server
                    self.client_socket.sendall(b"PAUSE")
                    paused_event.set()
                    self.pause_button.config(text="Resume broadcasts")
            except Exception as e:
                logger.error(f"Error sending pause/resume command: {e}")
                if self.client_socket:
                    self.client_socket.close()
                    self.client_socket = None
                    self.connection_status.set("Disconnected")
                    logger.debug("Attempting to reconnect...")
                    time.sleep(2)
                    self.connect_to_server()

    def update_pause_button(self, text):
        self.pause_button.config(text=text)

    def run(self):
        root = self.create_gui()
        tray_icon = self.create_tray_icon(root)

        # Start the audio streaming in separate thread
        audio_thread = threading.Thread(target=self.stream_audio, daemon=True)
        audio_thread.start()

        # Start tray icon in separate thread
        tray_thread = threading.Thread(target=tray_icon.run, daemon=True)
        tray_thread.start()

        try:
            root.protocol("WM_DELETE_WINDOW", root.withdraw)  # Hide window on close
            root.mainloop()
        finally:
            shutdown_event.set()
            tray_icon.stop()
            audio_thread.join()


if __name__ == "__main__":
    client = AudioCastClient(HOST, PORT, RETRY_DELAY, HEARTBEAT_ENABLED)
    client.run()



