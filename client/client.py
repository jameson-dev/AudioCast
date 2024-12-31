import socket
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

connection_status = None  # Global variable to track connection status

# PyAudio Instance
p = pyaudio.PyAudio()


def connect_to_server():
    while not shutdown_event.is_set():
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((HOST, PORT))
            logger.info(f"Connected to server at {HOST}:{PORT}")
            connection_status.set("Connected")
            return client_socket
        except ConnectionRefusedError:
            logger.warning(f"Connection refused. Retrying in {RETRY_DELAY} seconds...")
            connection_status.set("Disconnected")
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
        while not shutdown_event.is_set():
            if paused_event.is_set():
                time.sleep(0.1)    # Polling interval while paused
                continue

            if HEARTBEAT_ENABLED:
                client_socket.sendall(b"HEARTBEAT")

            # Receive audio data from server
            data = client_socket.recv(CHUNK_SIZE)
            if not data:
                break
            stream.write(data)
    except ConnectionRefusedError:
        logger.exception(f"Unable to connect to server at {HOST}:{PORT}. (Server already running?)")
        connection_status.set("Disconnected")
    except KeyboardInterrupt:
        logger.info(f"Streaming stopped by user")

    finally:
        client_socket.close()
        stream.stop_stream()
        stream.close()


def create_tray_icon():
    def on_quit():
        shutdown_event.set()
        tray_icon.stop()

    def open_gui():
        root.deiconify()

    # Create tray icon
    image = Image.new('RGB', (64, 64), color=(0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 16, 48, 48), fill=(255, 255, 255))

    menu = Menu(MenuItem('Open', open_gui), MenuItem('Quit', on_quit))
    tray_icon = Icon("AudioCast Client", image, "AudioCast", menu)
    return tray_icon


def create_gui():
    global connection_status

    def toggle_pause():
        if paused_event.is_set():
            paused_event.clear()
            pause_button.config(text="Pause alerts")
        else:
            paused_event.set()
            pause_button.config(text="Resume alerts")

    def close_gui():
        root.withdraw()

    root = Tk()
    root.title("AudioCast Client")
    root.geometry("300x150")

    # Initialise connection_status
    connection_status = StringVar(root, value="Disconnected")

    status_label = Label(root, textvariable=connection_status, font=("Arial", 12), fg="green")
    status_label.pack(pady=10)

    title_label = Label(root, text="AudioCast Client", font=("Arial", 16))
    title_label.pack(pady=10)

    pause_button = Button(root, text="Pause Notifications", command=toggle_pause)
    pause_button.pack(pady=5)

    exit_button = Button(root, text="Close to tray", command=close_gui)
    exit_button.pack(pady=5)

    root.withdraw()
    return root


if __name__ == "__main__":
    # Create and start GUI
    root = create_gui()
    tray_icon = create_tray_icon()

    # Start the audio streaming in separate thread
    audio_thread = threading.Thread(target=stream_audio, daemon=True)
    audio_thread.start()

    # Start tray icon in separate thread
    tray_thread = threading.Thread(target=tray_icon.run, daemon=True)
    tray_thread.start()

    try:
        root.protocol("WM_DELETE_WINDOW", root.withdraw)    # Hide window on close
        root.mainloop()
    finally:
        shutdown_event.set()
        tray_icon.stop()
        audio_thread.join()
