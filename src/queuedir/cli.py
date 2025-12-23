import argparse
import logging
import signal
import sys
from pathlib import Path

from .config import Config, load_config
from .executor import run_script
from .filestate import move_to_folder, wait_for_stable
from .watcher import FolderWatcher

logger = logging.getLogger("queuedir")
shutdown_requested = False


def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def signal_handler(signum, frame):
    global shutdown_requested
    shutdown_requested = True
    logger.info("Shutdown requested, finishing current job...")


def parse_args(args=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="queuedir",
        description="Folder-based job queue system",
    )
    parser.add_argument("-w", "--watch", required=True, help="Folder to monitor")
    parser.add_argument("-s", "--script", required=True, help="Script to execute")
    parser.add_argument("--done-dir", help="Destination for processed files")
    parser.add_argument("--failed-dir", help="Destination for failed files")
    parser.add_argument("--timeout", type=int, help="Script timeout in seconds")
    parser.add_argument("--poll-interval", type=float, help="Stability check interval")
    parser.add_argument("--once", action="store_true", help="Process existing and exit")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    return parser.parse_args(args)


def process_file(filepath: Path, config: Config) -> bool:
    if not filepath.exists():
        logger.warning(f"File no longer exists: {filepath}")
        return True

    logger.info(f"Processing: {filepath.name}")
    max_wait = config.timeout
    if not wait_for_stable(filepath, config.poll_interval, max_wait):
        logger.error(f"File not stable within timeout: {filepath}")
        move_to_folder(filepath, config.failed_dir)
        return False

    result = run_script(config.script_path, filepath, config.timeout)
    logger.debug(f"stdout: {result.stdout}")
    logger.debug(f"stderr: {result.stderr}")

    if result.exit_code == 0:
        logger.info(f"Success: {filepath.name} (took {result.duration:.1f}s)")
        move_to_folder(filepath, config.done_dir)
        return True
    else:
        reason = "timeout" if result.timed_out else f"exit code {result.exit_code}"
        logger.error(f"Failed: {filepath.name} ({reason})")
        if result.stderr:
            logger.error(f"stderr: {result.stderr}")
        move_to_folder(filepath, config.failed_dir)
        return False


def run(config: Config):
    global shutdown_requested

    config.done_dir.mkdir(parents=True, exist_ok=True)
    config.failed_dir.mkdir(parents=True, exist_ok=True)

    if not config.watch_dir.is_dir():
        logger.error(f"Watch directory does not exist: {config.watch_dir}")
        sys.exit(1)

    if not config.script_path.is_file():
        logger.error(f"Script does not exist: {config.script_path}")
        sys.exit(1)

    watcher = FolderWatcher(config.watch_dir, config.done_dir, config.failed_dir)
    watcher.scan_existing()

    if not config.once:
        watcher.start()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        while not shutdown_requested:
            filepath = watcher.get_file(timeout=1.0)
            if filepath:
                process_file(filepath, config)
                watcher.clear_seen(filepath)
            elif config.once and watcher.file_queue.empty():
                break
    finally:
        if not config.once:
            watcher.stop()

    logger.info("Shutdown complete")


def main(args=None):
    parsed = parse_args(args)
    setup_logging(parsed.verbose)
    config = load_config(
        watch_dir=parsed.watch,
        script_path=parsed.script,
        done_dir=parsed.done_dir,
        failed_dir=parsed.failed_dir,
        timeout=parsed.timeout,
        poll_interval=parsed.poll_interval,
        once=parsed.once,
        verbose=parsed.verbose,
    )
    run(config)


if __name__ == "__main__":
    main()
