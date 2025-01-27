import socket
import time
from loguru import logger
from gui import create_gui


def connect_to_server(host, port, reconnect_delay, shutdown_event, socket_lock):
    client_socket = None

    while not shutdown_event.is_set():
        try:
            if socket_lock.acquire(timeout=5):
                try:
                    logger.debug("Creating new socket...")
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.settimeout(5)
                    logger.info(f"Connecting to {host}:{port}...")
                    client_socket.connect((host, port))

                    logger.info(f"Connected to {host}:{port}")
                    return client_socket

                finally:
                    socket_lock.release()

        except (socket.error, OSError) as e:

            logger.error(f"Error in connect_to_server: {e}")
            time.sleep(reconnect_delay)

    return None
