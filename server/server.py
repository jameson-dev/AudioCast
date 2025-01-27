import threading
import pyaudio
import signal
from pathlib import Path
import argparse
from loguru import logger
from config import load_config
from audio_server import AudioServer
from helpers import check_dirs

parser = argparse.ArgumentParser(description="RFAStream Streaming Server")
parser.add_argument("--host", default="0.0.0.0", help="Server Hostname (Default: 0.0.0.0)")
parser.add_argument("--port", type=int, default=12345, help="Server Port (Default: 12345)")
parser.add_argument("--watchdog-folder", default="rfa", help="Folder to monitor for .rfa files")
parser.add_argument("--audio-files", default="wav-files", help="Folder where .wav files are stored")

# pyAudio settings
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

# pyAudio instance
p = pyaudio.PyAudio()

shutdown_event = threading.Event()


def signal_handler(signum, frame):
    logger.info(f"Signal {signum} received. Initiating shutdown...")
    shutdown_event.set()


def main():
    # Load configuration from config.json
    config = load_config()

    # Parse arguments
    args = parser.parse_args()

    # Override config values with command-line arguments if present
    config.update({
        'host': args.host or config['host'],
        'port': args.port or config['port'],
        'watchdog_folder': args.watchdog_folder or config['watchdog_folder'],
        'audio_files': args.audio_files or config['audio_files']
    })

    # Now use the values from config
    watchdog_folder = Path(config['watchdog_folder'])
    audio_files_folder = Path(config['audio_files'])
    host = config['host']
    port = config['port']

    # Check and create necessary directories
    check_dirs(watchdog_folder)
    check_dirs(audio_files_folder)

    # Start the server
    server = AudioServer(host, port, config['watchdog_folder'], config['audio_files'])
    server.start_folder_monitor()

    try:
        server.start()
    except Exception as e:
        logger.error(f"Server encountered an error: {e}")
    finally:
        server.shutdown()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)  # Handle Ctrl+C (SIGINT)
    signal.signal(signal.SIGTERM, signal_handler)  # Handle termination (SIGTERM)
    main()
