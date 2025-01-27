import os
from loguru import logger


def check_dirs(dir_path):
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
            logger.info(f"Directory missing. Creating now: {dir_path}")
        except OSError as e:
            logger.error(f"Failed to create directory ({dir_path}): {e}")
    else:
        logger.info(f"Directory exists ({dir_path}). Continuing")
