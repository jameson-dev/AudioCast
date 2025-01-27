import pyaudio
import time
import socket
import threading
from loguru import logger
from network import connect_to_server

CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

paused_event = threading.Event()
shutdown_event = threading.Event()

p = pyaudio.PyAudio()


def stream_audio(client, connection_status, broadcast_status, reconnect_delay, is_muted, client_socket):
    client.check_and_reconnect()  # Ensure fresh connection
    logger.debug("stream_audio called")
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True,
                    frames_per_buffer=CHUNK_SIZE)

    while not shutdown_event.is_set():
        if not client_socket or client_socket.fileno() == -1:  # Check if socket is invalid or closed
            logger.debug("No active socket, attempting to reconnect.")
            client_socket = connect_to_server(client.host, client.port, client.reconnect_delay, client.shutdown_event,
                                              client.socket_lock)
            if client_socket:
                connection_status.set("Connected")
                broadcast_status.set("Broadcast Active")
            else:
                connection_status.set("Disconnected")
                broadcast_status.set("Not connected")
            continue

        if paused_event.is_set():
            logger.info("Broadcast paused. Skipping broadcasts.")
            broadcast_status.set("Broadcast Paused")
            while paused_event.is_set() and not shutdown_event.is_set():
                time.sleep(0.1)
            continue

        try:
            if client_socket and client_socket.fileno() != -1:
                data = client_socket.recv(CHUNK_SIZE)
                if not data:
                    logger.warning("Server disconnected.")
                    connection_status.set("Disconnected")
                    broadcast_status.set("Not connected")
                    client_socket.close()
                    client_socket = None
                    continue

                if is_muted:
                    continue
                else:
                    stream.write(data)
            else:
                logger.warning("Invalid socket. Reconnecting...")
                connection_status.set("Disconnected")
                broadcast_status.set("Not connected")
                time.sleep(reconnect_delay)
        except socket.timeout:
            pass
        except socket.error as e:
            logger.error(f"Socket error: {e}")
            if client_socket:
                client_socket.close()
                connection_status.set("Disconnected")
                broadcast_status.set("Not connected")
            client_socket = None
        except Exception as e:
            logger.error(f"Unexpected error in streaming: {e}")
            if client_socket:
                client_socket.close()
                connection_status.set("Disconnected")
                broadcast_status.set("Not connected")
            client_socket = None

        if client_socket is None:
            connection_status.set("Disconnected")
            broadcast_status.set("Not connected")
            logger.debug("Attempting to reconnect...")
            time.sleep(reconnect_delay)

    stream.stop_stream()
    stream.close()
    if client_socket:
        client_socket.close()


def cleanup_audio():
    logger.info("Terminating audio stream...")
    p.terminate()
