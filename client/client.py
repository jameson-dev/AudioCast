import socket
import time

import pyaudio
from loguru import logger
import argparse

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

# PyAudio Instance
p = pyaudio.PyAudio()


def connect_to_server():
    while True:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((HOST, PORT))
            logger.info(f"Connected to server at {HOST}:{PORT}")
            return client_socket
        except ConnectionRefusedError:
            logger.warning(f"Connection refused. Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)


def stream_audio():
    # Open a stream for playback
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True,
                    frames_per_buffer=CHUNK_SIZE)

    client_socket = connect_to_server()

    try:
        while True:
            if HEARTBEAT_ENABLED:
                client_socket.sendall(b"HEARTBEAT")

            # Receive audio data from server
            data = client_socket.recv(CHUNK_SIZE)
            if not data:
                break
            stream.write(data)
    except ConnectionRefusedError:
        logger.exception(f"Unable to connect to server at {HOST}:{PORT}. (Server already running?)")
    except KeyboardInterrupt:
        logger.info(f"Streaming stopped by user")

    finally:
        client_socket.close()
        stream.stop_stream()
        stream.close()


if __name__ == "__main__":
    stream_audio()
