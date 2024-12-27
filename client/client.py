import socket
import pyaudio
from loguru import logger

# Server settings
HOST = "localhost"
PORT = 12345

# PyAudio settings
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

# PyAudio Instance
p = pyaudio.PyAudio()


def stream_audio():
    # Open a stream for playback
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True,
                    frames_per_buffer=CHUNK_SIZE)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    logger.info(f"Connected to server at {HOST}:{PORT}")

    try:
        while True:
            # Receive audio data from server
            data = client_socket.recv(CHUNK_SIZE)
            if not data:
                break
            stream.write(data)
    except KeyboardInterrupt:
        logger.info(f"Streaming stopped")

    finally:
        client_socket.close()
        stream.stop_stream()
        stream.close()


if __name__ == "__main__":
    stream_audio()
