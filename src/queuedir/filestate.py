import logging
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def get_file_state(filepath: Path) -> Optional[Tuple[int, float]]:
    try:
        stat = filepath.stat()
        return (stat.st_size, stat.st_mtime)
    except OSError:
        return None


def wait_for_stable(filepath: Path, interval: float, max_wait: float) -> bool:
    start = time.monotonic()
    prev_state = get_file_state(filepath)
    if prev_state is None:
        return False

    while time.monotonic() - start < max_wait:
        time.sleep(interval)
        curr_state = get_file_state(filepath)
        if curr_state is None:
            return False
        if curr_state == prev_state:
            logger.debug(f"File stable: {filepath}")
            return True
        prev_state = curr_state
        logger.debug(f"File still changing: {filepath}")

    return False


def move_to_folder(filepath: Path, destination_folder: Path) -> Path:
    destination_folder.mkdir(parents=True, exist_ok=True)
    dest_path = destination_folder / filepath.name
    if dest_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        stem = filepath.stem
        suffix = filepath.suffix
        dest_path = destination_folder / f"{stem}_{timestamp}{suffix}"
    shutil.move(str(filepath), str(dest_path))
    logger.debug(f"Moved {filepath} to {dest_path}")
    return dest_path
