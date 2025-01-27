import os
import signal
import socket
import threading
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
        self.broadcast_paused = False
        self.shutdown_event = threading.Event()
        self.paused_event = threading.Event()
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
            self.broadcast_status.set("Broadcast Active")
        else:
            self.connection_status.set("Disconnected")
            self.broadcast_status.set("Not connected.")
        return self.client_socket

    def check_and_reconnect(self):
        logger.debug("Checking connection status...")
        try:
            # Test the socket connection
            self.client_socket.sendall(b"PING")
        except (socket.error, ConnectionResetError, BrokenPipeError) as e:
            logger.warning(f"Connection issue detected: {e}. Reconnecting...")
            self.reconnect_to_server()

    def reconnect_to_server(self):
        try:
            # Safely close the existing socket if it exists
            if self.client_socket:
                logger.debug("Closing existing socket before reconnecting.")
                self.client_socket.close()
                self.client_socket = None

            # Attempt to reconnect to the server
            self.client_socket = connect_to_server(self.host, self.port, self.reconnect_delay, self.shutdown_event, self.socket_lock)
            return self.client_socket
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            return None

    def request_pause_state(self, client_socket):
        try:
            client_socket.sendall(b"GET_PAUSE_STATE")  # Send request for current pause state
            response = client_socket.recv(1024).decode().strip()  # Receive response
            if response == "PAUSED":
                self.paused_event.set()  # Pause broadcast
                self.broadcast_status.set("Broadcast Paused")
            else:
                self.paused_event.clear()  # Resume broadcast
                self.broadcast_status.set("Broadcast Active")
        except Exception as e:
            logger.error(f"Error requesting pause state: {e}")

    def toggle_client_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            logger.info("Client muted.")
            self.mute_button.config(text="Unmute Client")
        else:
            logger.info("Client unmuted.")
            self.mute_button.config(text="Mute Client")

    def toggle_broadcast_pause(self):
        self.check_and_reconnect()
        if not self.client_socket or self.client_socket.fileno() == -1:  # Check if socket is invalid
            self.client_socket = self.reconnect_to_server()  # Attempt to reconnect
            if not self.client_socket:
                logger.error("Reconnection failed, cannot send command.")
                return

        if self.broadcast_paused:
            logger.debug("Sending RESUME command to the server...")
            try:
                self.client_socket.sendall(b"RESUME")
                self.broadcast_paused = False
                self.pause_button.config(text="Pause broadcast")
                self.broadcast_status.set("Broadcast Active")
            except Exception as e:
                logger.error(f"Error sending resume command: {e}")
        else:
            logger.debug("Sending PAUSE command to the server...")
            try:
                self.client_socket.sendall(b"PAUSE")
                self.broadcast_paused = True
                self.pause_button.config(text="Resume broadcast")
                self.broadcast_status.set("Broadcast Paused")
            except Exception as e:
                logger.error(f"Error sending pause command: {e}")

    def run(self):
        root = create_gui(self)
        tray_icon = create_tray_icon(self, root)
        self.connect()

        # Start audio thread
        audio_thread = threading.Thread(target=stream_audio, args=(self, self.connection_status, self.broadcast_status, self.reconnect_delay, self.is_muted, self.client_socket), daemon=True)
        audio_thread.start()

        # Start tray icon thread
        tray_thread = threading.Thread(target=tray_icon.run, daemon=True)
        tray_thread.start()

        try:
            root.protocol("WM_DELETE_WINDOW", root.withdraw)
            root.mainloop()
        finally:
            logger.info("Shutting down client...")
            self.cleanup()
            tray_icon.stop()
            audio_thread.join()

    def cleanup(self):
        logger.info("Cleaning up resources...")
        self.shutdown_event.set()
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
    signal.signal(signal.SIGINT, lambda signum, frame: client.cleanup())
    signal.signal(signal.SIGTERM, lambda signum, frame: client.cleanup())

    shutdown_event = threading.Event()
    config = load_config()

    args = parser.parse_args()
    for key, value in vars(args).items():
        default_value = parser.get_default(key)
        if value != default_value:
            config[key] = value

    config.update({
        'host': config['host'],
        'port': int(config['port']),
        'reconnect_delay': int(config['reconnect_delay']),
        'heartbeat_enabled': config['heartbeat_enabled'],
        'start_muted': config['start_muted']
    })

    host = config['host']
    port = config['port']
    reconnect_delay = config['reconnect_delay']
    heartbeat_enabled = config['heartbeat_enabled']

    client = RFAStreamClient(host, port, reconnect_delay, heartbeat_enabled)
    client.run()


if __name__ == "__main__":
    main()
