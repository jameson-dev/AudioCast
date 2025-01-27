import os
import re
from loguru import logger
from watchdog.events import FileSystemEventHandler, DirCreatedEvent, FileCreatedEvent
from typing import Union


class FileHandler(FileSystemEventHandler):
    def __init__(self, server, audio_files_folder):
        self.server = server
        self.audio_files_folder = audio_files_folder  # Store it as an instance variable

    def on_created(self, event: Union[DirCreatedEvent, FileCreatedEvent]) -> None:
        if event.is_directory:
            return
        if event.src_path.endswith(".rfa"):
            logger.info(f"New .rfa file detected: {event.src_path}")
            self.handle_rfa_file(event.src_path)

    def handle_rfa_file(self, rfa_file_path):
        base_name = os.path.splitext(os.path.basename(rfa_file_path))[0]

        # Extract the meaningful part of the filename (before the timestamp and ID)
        match = re.match(r"(P[1-3])_([a-zA-Z0-9_]+)_.*", base_name)
        if not match:
            logger.error(f"Filename format is unrecognized: {base_name}")
            return

        keyword_part = match.group(2)  # Extract the part after the priority
        normalized_keyword = keyword_part.replace("_", " ").lower().strip()

        # Check for Priority in filename:
        incident_priority = base_name[:2]   # Get P1, P2 or P3 from the start of the filename

        logger.info(f"Priority: {incident_priority}, Incident: {keyword_part}")

        # Replace spaces with underscores for .wav file matching
        inc_type_wav = normalized_keyword.replace(" ", "_") + ".wav"
        incident_priority_wav = f"{incident_priority}.wav"

        audio_file_path = os.path.join(self.audio_files_folder, inc_type_wav)
        inc_priority_audio_file_path = os.path.join(self.audio_files_folder, incident_priority_wav)

        if os.path.exists(audio_file_path) and os.path.exists(inc_priority_audio_file_path):
            logger.debug(f"Found audio file {audio_file_path}")
            logger.debug(f"Found priority audio file {inc_priority_audio_file_path}")
            logger.info(f"Streaming {inc_priority_audio_file_path} and {audio_file_path}")
            self.stream_audio_sequentially(audio_file_path, inc_priority_audio_file_path)
        # If priority wav file not found, just stream incident type wav
        elif os.path.exists(audio_file_path) and not os.path.exists(inc_priority_audio_file_path):
            logger.warning(f"Incident Priority ({inc_priority_audio_file_path}) could not be found. Only playing incident type ({audio_file_path})")
            self.stream_audio(audio_file_path)
        else:
            logger.error(f"Error: Audio file '{audio_file_path}' not found.")

    def stream_audio_sequentially(self, audio_file_path, priority_audio_path):
        """Stream two audio files sequentially to the client."""
        try:
            logger.info(f"Streaming audio files")

            # Send the incident priority audio file
            self.stream_audio(priority_audio_path)

            # Send the incident type audio file
            self.stream_audio(audio_file_path)

            logger.info("Both audio files streamed successfully.")
        except FileNotFoundError as e:
            logger.error(f"Error streaming audio: {e}")

    def stream_audio(self, file_path):
        try:
            with open(file_path, 'rb') as audio_file:
                while chunk := audio_file.read(1024):
                    # Send chunks of audio to all connected clients
                    self.server.broadcast_audio(chunk)
        except FileNotFoundError:
            logger.error(f"Audio file not found: {file_path}")
