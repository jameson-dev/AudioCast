import pyaudio
import time
import socket
import threading
from loguru import logger
from network import connect_to_server

# PyAudio settings
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

paused_event = threading.Event()
shutdown_event = threading.Event()

# PyAudio Instance
p = pyaudio.PyAudio()


def stream_audio(client, connection_status, broadcast_status, reconnect_delay, is_muted):
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
                client_socket = connect_to_server(client.host, client.port, client.reconnect_delay, client.shutdown_event, client.socket_lock)
                if client_socket:
                    connection_status.set("Connected")

                    # Wait for the server's control message about pause/resume state
                    control_message = client_socket.recv(1024).decode().strip()
                    if control_message.startswith("CONTROL:"):
                        if "PAUSED" in control_message:
                            paused_event.set()
                            client.pause_button.config(text="Resume broadcast")
                            broadcast_status.set("Broadcast Paused")
                        else:
                            paused_event.clear()
                            client.pause_button.config(text="Pause broadcast")
                            broadcast_status.set("Broadcast Active")
                    else:
                        logger.warning(f"Unexpected control message received: {control_message}")
                else:
                    connection_status.set("Disconnected")
                    broadcast_status.set("Not connected")
            except Exception as e:
                logger.error(f"Failed to connect: {e}")
                connection_status.set("Disconnected")
                time.sleep(reconnect_delay)
                continue

        if paused_event.is_set():
            logger.info("Broadcast paused. Skipping any broadcasts.")
            broadcast_status.set("Broadcast Paused")
            while paused_event.is_set() and not shutdown_event.is_set():
                time.sleep(0.1)  # Wait for the pause to be cleared
            continue

        try:
            data = client_socket.recv(CHUNK_SIZE)
            if not data:
                logger.warning("Server disconnected.")
                connection_status.set("Disconnected")
                client_socket.close()
                client_socket = None
                continue

            if is_muted:
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
            time.sleep(reconnect_delay)

    stream.stop_stream()
    stream.close()
    if client_socket:
        client_socket.close()


def cleanup_audio():
    logger.info("Terminating audio stream...")
    p.terminate()