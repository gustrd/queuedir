import fnmatch
import logging
import queue
from pathlib import Path
from typing import Set

from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

IGNORE_PATTERNS = ("*.tmp", "*.part", "~*", ".*")


def should_ignore(filename: str) -> bool:
    for pattern in IGNORE_PATTERNS:
        if fnmatch.fnmatch(filename, pattern):
            return True
    return False


class QueueHandler(FileSystemEventHandler):
    def __init__(self, file_queue: queue.Queue, watch_dir: Path, exclude_dirs: Set[Path]):
        self.file_queue = file_queue
        self.watch_dir = watch_dir
        self.exclude_dirs = exclude_dirs
        self._seen: Set[Path] = set()

    def _should_process(self, path: Path) -> bool:
        if not path.is_file():
            return False
        if should_ignore(path.name):
            return False
        for exclude in self.exclude_dirs:
            try:
                path.relative_to(exclude)
                return False
            except ValueError:
                pass
        return True

    def _enqueue(self, path: Path):
        if path in self._seen:
            return
        if self._should_process(path):
            self._seen.add(path)
            self.file_queue.put(path)
            logger.debug(f"Enqueued: {path}")

    def on_created(self, event):
        if isinstance(event, FileCreatedEvent):
            self._enqueue(Path(event.src_path))

    def on_moved(self, event):
        if isinstance(event, FileMovedEvent):
            self._enqueue(Path(event.dest_path))

    def clear_seen(self, path: Path):
        self._seen.discard(path)


class FolderWatcher:
    def __init__(self, watch_dir: Path, done_dir: Path, failed_dir: Path):
        self.watch_dir = watch_dir
        self.done_dir = done_dir
        self.failed_dir = failed_dir
        self.file_queue: queue.Queue = queue.Queue()
        self.handler = QueueHandler(
            self.file_queue,
            watch_dir,
            {done_dir, failed_dir},
        )
        self.observer = Observer()

    def scan_existing(self):
        for path in self.watch_dir.iterdir():
            if path.is_file() and not should_ignore(path.name):
                if path not in self.handler._seen:
                    self.handler._enqueue(path)
        logger.info(f"Scanned existing files: {self.file_queue.qsize()} found")

    def start(self):
        self.observer.schedule(self.handler, str(self.watch_dir), recursive=False)
        self.observer.start()
        logger.info(f"Watching: {self.watch_dir}")

    def stop(self):
        self.observer.stop()
        self.observer.join()
        logger.info("Watcher stopped")

    def get_file(self, timeout: float = 1.0) -> Path | None:
        try:
            return self.file_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def clear_seen(self, path: Path):
        self.handler.clear_seen(path)
