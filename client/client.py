import os
import signal
import socket
import threading
import time
import argparse
from loguru import logger
from config import load_config
from network import connect_to_server
from audio import stream_audio, cleanup_audio
from gui import create_gui, create_tray_icon


parser = argparse.ArgumentParser(description="RFAStream Client")
parser.add_argument("--host", default='127.0.0.1', help="Server Hostname (Default: 127.0.0.1)")
parser.add_argument("--port", type=int, default=12345, help="Server Port (Default: 12345)")
parser.add_argument("--retry", type=int, default=5, help="Reconnect delay in seconds (Default: 5 seconds)")
parser.add_argument("--heartbeat", type=bool, default=True, help="Enable client heartbeat (Default: True)")
parser.add_argument("--start-muted", default=False, help="Whether the client is muted by default")


class RFAStreamClient:
    def __init__(self, host, port, retry_delay, heartbeat_enabled):
        self.host = host
        self.port = port
        self.reconnect_delay = retry_delay
        self.heartbeat_enabled = heartbeat_enabled

        self.client_socket = None

        self.shutdown_event = threading.Event()
        self.paused_event = threading.Event()

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

    def connect(self):
        self.client_socket = connect_to_server(self.host, self.port, self.reconnect_delay, self.shutdown_event, self.socket_lock)

        if self.client_socket:
            self.connection_status.set("Connected")
        else:
            self.connection_status.set("Disconnected")
        return self.client_socket

    def toggle_client_mute(self):
        self.is_muted = not self.is_muted

        # Update the mute button text based on mute state
        if self.is_muted:
            logger.info("Client muted.")
            self.mute_button.config(text="Unmute Client")
        else:
            logger.info("Client unmuted.")
            self.mute_button.config(text="Mute Client")

    def toggle_broadcast_pause(self):
        if self.client_socket:
            try:
                if self.paused_event.is_set():
                    # Send RESUME command to server
                    self.client_socket.sendall(b"RESUME")
                    self.paused_event.clear()
                    self.broadcast_status.set("Broadcast Active")
                    logger.info("Broadcast resumed. Listening for audio data")
                    self.pause_button.config(text="Pause broadcast")
                else:
                    # Send PAUSE command to server
                    self.client_socket.sendall(b"PAUSE")
                    self.paused_event.set()
                    self.broadcast_status.set("Broadcast Paused")
                    logger.info("Broadcast paused. All clients paused.")
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
                    connect_to_server(self.host, self.port, self.reconnect_delay, self.shutdown_event, self.socket_lock)

    def run(self):
        root = create_gui(self)
        tray_icon = create_tray_icon(self, root)

        self.connect()

        # Start the audio streaming in separate thread
        audio_thread = threading.Thread(target=stream_audio, args=(self, self.connection_status, self.broadcast_status, self.reconnect_delay, self.is_muted, self.client_socket), daemon=True)
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

        cleanup_audio()

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

    # Initialise shutdown event and pass to client
    shutdown_event = threading.Event()

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
