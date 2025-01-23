import os
import signal
import socket
import sys
import threading
import time
import pyaudio
import argparse
import json
from loguru import logger
from tkinter import Tk, Button, Label, StringVar
from pystray import Icon, MenuItem, Menu
from PIL import Image


parser = argparse.ArgumentParser(description="RFAStream Client")
parser.add_argument("--host", default='127.0.0.1', help="Server Hostname (Default: 127.0.0.1)")
parser.add_argument("--port", type=int, default=12345, help="Server Port (Default: 12345)")
parser.add_argument("--retry", type=int, default=5, help="Reconnect delay in seconds (Default: 5 seconds)")
parser.add_argument("--heartbeat", type=bool, default=True, help="Enable client heartbeat (Default: True)")
parser.add_argument("--start-muted", default=False, help="Whether the client is muted by default")

# PyAudio settings
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

paused_event = threading.Event()
shutdown_event = threading.Event()

# PyAudio Instance
p = pyaudio.PyAudio()


def load_config(config_path='client-config.json'):
    # Default config values
    default_config = {
        'host': '127.0.0.1',
        'port': 12345,
        'reconnect_delay': 5,
        'heartbeat_enabled': True,
        'start_muted': False
    }

    # Check if the config file exists
    if os.path.exists(config_path):
        # If the file exists, load it
        with open(config_path, 'r') as config_file:
            try:
                config = json.load(config_file)
                logger.info("Client configuration loaded successfully.")
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


class RFAStreamClient:
    def __init__(self, host, port, retry_delay, heartbeat_enabled):
        self.host = host
        self.port = port
        self.reconnect_delay = retry_delay
        self.heartbeat_enabled = heartbeat_enabled

        self.client_socket = None

        self.shutdown_event = shutdown_event
        self.paused_event = paused_event

        # Initialize GUI-related variables
        self.connection_status = None
        self.broadcast_status = None
        self.pause_button = None
        self.mute_button = None
        self.is_muted = False
        self.root = None

        self.socket_lock = threading.Lock()

        config = load_config()
        if config.get('start_muted', False):
            self.is_muted = True
            logger.info("Client is muted by default")
        else:
            logger.info("Client is not muted by default")

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
                        logger.info(f"Connecting to {self.host}:{self.port}...")

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
                self.broadcast_status.set("Not connected")
                time.sleep(self.reconnect_delay)

        logger.debug("Exiting connect_to_server due to shutdown event.")
        return None

    def toggle_client_mute(self):
        self.is_muted = not self.is_muted

        # Update the mute button text based on mute state
        if self.is_muted:
            logger.info("Client muted.")
            self.mute_button.config(text="Unmute Client")
        else:
            logger.info("Client unmuted.")
            self.mute_button.config(text="Mute Client")

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
                    logger.debug("No active socket, attempting to reconnect.")
                    client_socket = self.connect_to_server()
                    if client_socket:
                        self.connection_status.set("Connected")

                        # Wait for the server's control message about pause/resume state
                        control_message = client_socket.recv(1024).decode().strip()
                        if control_message.startswith("CONTROL:"):
                            if "PAUSED" in control_message:
                                paused_event.set()
                                self.pause_button.config(text="Resume broadcast")
                                self.broadcast_status.set("Broadcast Paused")
                            else:
                                paused_event.clear()
                                self.pause_button.config(text="Pause broadcast")
                                self.broadcast_status.set("Broadcast Active")
                        else:
                            logger.warning(f"Unexpected control message received: {control_message}")
                    else:
                        self.connection_status.set("Disconnected")
                        self.broadcast_status.set("Not connected")
                except Exception as e:
                    logger.error(f"Failed to connect: {e}")
                    self.connection_status.set("Disconnected")
                    time.sleep(self.reconnect_delay)
                    continue

            if paused_event.is_set():
                logger.info("Broadcast paused. Skipping any broadcasts.")
                self.broadcast_status.set("Broadcast Paused")
                while paused_event.is_set() and not shutdown_event.is_set():
                    time.sleep(0.1)  # Wait for the pause to be cleared
                continue

            try:
                data = client_socket.recv(CHUNK_SIZE)
                if not data:
                    logger.warning("Server disconnected.")
                    self.connection_status.set("Disconnected")
                    client_socket.close()
                    client_socket = None
                    continue

                if self.is_muted:
                    # Mute audio by not writing and data to stream
                    continue
                else:
                    stream.write(data)

            except socket.timeout:
                pass
            except socket.error as e:
                logger.error(f"Socket error occurred: {e}")
                if client_socket:
                    client_socket.close()
                client_socket = None
            except Exception as e:
                logger.error(f"Unexpected error in streaming: {e}")
                if client_socket:
                    client_socket.close()
                client_socket = None

            # Check if the client_socket is still valid and try reconnecting if not
            if client_socket is None:
                logger.debug("Attempting to reconnect to server...")
                time.sleep(self.reconnect_delay)

        stream.stop_stream()
        stream.close()
        if client_socket:
            client_socket.close()

    def create_tray_icon(self, root):
        def on_quit():
            self.cleanup()
            sys.exit(0)

        def open_gui():
            root.deiconify()

        # Create tray icon
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'rfastream.ico')
        icon_image = Image.open(icon_path)

        menu = Menu(MenuItem('Open', open_gui), MenuItem('Quit', on_quit))

        tray_icon = Icon("RFAStream Client", icon_image, "RFAStream", menu)

        return tray_icon

    def create_gui(self):
        root = Tk()
        root.title("RFAStream Client")
        root.resizable(False, False)

        root.iconbitmap("..\\assets\\rfastream.ico")

        # Calculate the position for the bottom-right corner
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = 300
        window_height = 215
        position_x = screen_width - window_width - 10  # 10px margin from the edge
        position_y = screen_height - window_height - 100  # 100px margin from the taskbar

        # Set the position
        root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")

        self.connection_status = StringVar()
        self.connection_status.set("Disconnected")

        self.broadcast_status = StringVar()
        self.broadcast_status.set("Finding Broadcast Status...")

        title_label = Label(root, text="RFAStream Client", font=("Arial", 16))
        title_label.pack(pady=(5, 0))

        status_label = Label(root, textvariable=self.connection_status, font=("Arial", 12), fg="green")
        status_label.pack(pady=(0, 10))

        broadcast_status_label = Label(root, textvariable=self.broadcast_status, font=("Arial", 10), fg="black")
        broadcast_status_label.pack(pady=(0, 15))

        self.pause_button = Button(root, text="Pause Notifications", command=self.toggle_broadcast_pause)
        self.pause_button.pack(pady=5)

        mute_button_text = "Unmute Client" if self.is_muted else "Mute Client"
        self.mute_button = Button(root, text=mute_button_text, command=self.toggle_client_mute)
        self.mute_button.pack(pady=5)

        exit_button = Button(root, text="Hide", command=root.withdraw)
        exit_button.pack(pady=5)

        root.withdraw()
        return root

    def toggle_broadcast_pause(self):
        if self.client_socket:
            try:
                if paused_event.is_set():
                    # Send RESUME command to server
                    self.client_socket.sendall(b"RESUME")
                    paused_event.clear()
                    self.broadcast_status.set("Broadcast Active")
                    logger.info("Broadcast resumed. Listening for audio data")
                    self.pause_button.config(text="Pause broadcast")
                else:
                    # Send PAUSE command to server
                    self.client_socket.sendall(b"PAUSE")
                    paused_event.set()
                    self.pause_button.config(text="Resume broadcast")
            except Exception as e:
                logger.error(f"Error sending pause/resume command: {e}")
                if self.client_socket:
                    self.client_socket.close()
                    self.client_socket = None
                    self.connection_status.set("Disconnected")
                    self.broadcast_status.set("Not connected")
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
            logger.info("Shutting down client...")
            self.cleanup()
            tray_icon.stop()
            audio_thread.join()

    def cleanup(self):
        logger.info("Cleaning up resources...")

        # Signal all threads to stop
        self.shutdown_event.set()

        # Close the socket if it's open
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
                logger.info("Client socket closed.")
            except Exception as e:
                logger.error(f"Error closing socket: {e}")

        p.terminate()

        try:
            if self.root:
                self.root.quit()
                self.root.destroy()
        except Exception as e:
            logger.error(f"Error destroying Tkinter root: {e}")

        logger.info("Active threads during cleanup:")
        for thread in threading.enumerate():
            logger.info(f"Thread: {thread.name}, Alive: {thread.is_alive()}")
        logger.info("Resources cleaned up.")

        logger.info("Forcing process termination.")
        os.kill(os.getpid(), signal.SIGTERM)


def main():

    # Handle shutdown signals
    signal.signal(signal.SIGINT, lambda signum, frame: client.cleanup())
    signal.signal(signal.SIGTERM, lambda signum, frame: client.cleanup())

    # Load configuration from config.json
    config = load_config()

    # Parse arguments
    args = parser.parse_args()

    # Only update config with explicitly provided arguments
    for key, value in vars(args).items():
        default_value = parser.get_default(key)
        if value != default_value:  # Only override if the argument is explicitly set
            config[key] = value

    # Override config values with command-line arguments if present
    config.update({
        'host': config['host'],
        'port': int(config['port']),
        'reconnect_delay': int(config['reconnect_delay']),
        'heartbeat_enabled': config['heartbeat_enabled'],
        'start_muted': config['start_muted']
    })

    # Server settings
    host = config['host']
    port = config['port']
    reconnect_delay = config['reconnect_delay']
    heartbeat_enabled = config['heartbeat_enabled']

    client = RFAStreamClient(host, port, reconnect_delay, heartbeat_enabled)
    client.run()


if __name__ == "__main__":
    main()
