import socket
import time
from loguru import logger


def connect_to_server(host, port, reconnect_delay, shutdown_event, socket_lock):
    client_socket = None

    while not shutdown_event.is_set():
        try:
            if socket_lock.acquire(timeout=5):  # Timeout for acquiring the socket lock
                try:
                    if client_socket:
                        logger.debug("Closing existing socket before reconnecting.")
                        client_socket.close()
                        client_socket = None

                    # Create a new socket and connect
                    logger.debug("Creating a new socket...")
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.settimeout(5)
                    logger.info(f"Connecting to {host}:{port}...")
                    client_socket.connect((host, port))

                    logger.info(f"Connected to {host}:{port}")
                    return client_socket  # Return the successful socket connection

                finally:
                    socket_lock.release()  # Always release the socket lock

        except (socket.error, OSError) as e:
            # Error handling and retry mechanism in case of failure
            logger.error(f"Error in connect_to_server: {e}")
            time.sleep(reconnect_delay)  # Wait before retrying

    return None  # Return None if shutdown event is triggered
