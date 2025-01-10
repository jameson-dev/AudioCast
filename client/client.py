import os
import signal
import socket
import sys
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

# Handle shutdown signals
signal.signal(signal.SIGINT, lambda signum, frame: client.cleanup())
signal.signal(signal.SIGTERM, lambda signum, frame: client.cleanup())


class AudioCastClient:
    def __init__(self, host, port, retry_delay, heartbeat_enabled):
        self.host = host
        self.port = port
        self.retry_delay = retry_delay
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
                self.broadcast_status.set("Not connected")
                time.sleep(self.retry_delay)

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
                    time.sleep(self.retry_delay)
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
                time.sleep(self.retry_delay)

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
        icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'audiocast.ico')
        icon_image = Image.open(icon_path)

        menu = Menu(MenuItem('Open', open_gui), MenuItem('Quit', on_quit))

        tray_icon = Icon("AudioCast Client", icon_image, "AudioCast", menu)

        return tray_icon

    def create_gui(self):
        root = Tk()
        root.title("AudioCast Client")
        root.resizable(False, False)

        root.iconbitmap("..\\assets\\audiocast.ico")

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

        title_label = Label(root, text="AudioCast Client", font=("Arial", 16))
        title_label.pack(pady=(5, 0))

        status_label = Label(root, textvariable=self.connection_status, font=("Arial", 12), fg="green")
        status_label.pack(pady=(0, 10))

        broadcast_status_label = Label(root, textvariable=self.broadcast_status, font=("Arial", 10), fg="black")
        broadcast_status_label.pack(pady=(0, 15))

        self.pause_button = Button(root, text="Pause Notifications", command=self.toggle_broadcast_pause)
        self.pause_button.pack(pady=5)

        self.mute_button = Button(root, text="Mute Client", command=self.toggle_client_mute)
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


if __name__ == "__main__":
    client = AudioCastClient(HOST, PORT, RETRY_DELAY, HEARTBEAT_ENABLED)
    client.run()



