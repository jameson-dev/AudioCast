import json
import os
from loguru import logger


def load_config(config_path='server-config.json'):
    # Default config values
    default_config = {
        'host': '0.0.0.0',
        'port': 12345,
        'watchdog_folder': 'rfa',
        'audio_files': 'wav-files'
    }

    # Check if the config file exists
    if os.path.exists(config_path):
        # If the file exists, load it
        with open(config_path, 'r') as config_file:
            try:
                config = json.load(config_file)
                logger.info("Server configuration loaded successfully.")
                return config
            except json.JSONDecodeError:
                logger.error("Invalid JSON format in config file. Using default settings.")
                return default_config
    else:
        # If the file does not exist, create it with default values
        with open(config_path, 'w') as config_file:
            json.dump(default_config, config_file, indent=4)
        logger.warning(f"Config file '{config_path}' not found. Creating it now..")
        return default_config
