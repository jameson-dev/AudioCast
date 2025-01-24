import os
import json
from loguru import logger


def load_config(config_file_name='client-config.json'):

    # Use the AppData folder to store the config file
    appdata_folder = os.getenv('APPDATA')
    config_path = os.path.join(appdata_folder, 'RFAStream', config_file_name)

    # Default config values
    default_config = {
        'host': '127.0.0.1',
        'port': 12345,
        'reconnect_delay': 5,
        'heartbeat_enabled': True,
        'start_muted': False
    }

    # Check if the config file exists
    if os.path.exists(config_path):
        # If the file exists, load it
        with open(config_path, 'r') as config_file:
            try:
                config = json.load(config_file)
                logger.info("Client configuration loaded successfully.")
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
