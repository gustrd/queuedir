\# IMPLEMENTATION\_PLAN: QueueDir



\## Project Overview



QueueDir is a lightweight, cross-platform (Windows/Linux) folder-based job queue system written in Python. It monitors a designated input folder and executes a user-specified script for each file that appears, passing the file path as an argument. Files are processed sequentially in FIFO order, with clear lifecycle management (pending → processing → done/failed).



\## Core Behavior



The daemon watches a folder for new files. When a file arrives and stabilizes (no longer being written to), QueueDir invokes the configured script with the file's absolute path as the first argument. Upon successful execution (exit code 0), the file moves to a `done/` subfolder. On failure (non-zero exit), it moves to `failed/`. The system must handle edge cases: partial uploads, locked files, script timeouts, and graceful shutdown via SIGINT/SIGTERM.



\## Directory Structure



```

queuedir/

├── queuedir/

│   ├── \\\_\\\_init\\\_\\\_.py

│   ├── \\\_\\\_main\\\_\\\_.py        # Entry point for `python -m queuedir`

│   ├── cli.py             # Argument parsing and CLI interface

│   ├── watcher.py         # Folder monitoring logic

│   ├── executor.py        # Script execution and subprocess handling

│   ├── filestate.py       # File stability detection and state management

│   └── config.py          # Configuration handling (CLI args, env vars, config file)

├── tests/

│   ├── test\\\_watcher.py

│   ├── test\\\_executor.py

│   └── test\\\_integration.py

├── pyproject.toml

├── README.md

└── LICENSE

```



\## Dependencies



Use `watchdog` for filesystem monitoring — it abstracts platform differences (inotify on Linux, ReadDirectoryChangesW on Windows, FSEvents on macOS). For subprocess execution, the standard library `subprocess` module suffices. No external queue infrastructure (Redis, RabbitMQ) is required; the filesystem itself acts as the queue.



Minimal dependencies: `watchdog>=3.0.0` only. Target Python 3.9+.



\## Component Specifications



\### cli.py



Accept the following arguments via argparse:



\- `--watch` / `-w`: Path to the folder to monitor (required)

\- `--script` / `-s`: Path to the script to execute (required)

\- `--done-dir`: Destination for successfully processed files (default: `{watch}/done`)

\- `--failed-dir`: Destination for failed files (default: `{watch}/failed`)

\- `--timeout`: Maximum seconds to wait for script execution (default: 1200)

\- `--poll-interval`: Seconds between stability checks for new files (default: 2)

\- `--once`: Process existing files and exit without watching (flag)

\- `--verbose` / `-v`: Enable debug logging



The CLI should also support a `--config` option pointing to a YAML or TOML file for persistent configuration.



\### watcher.py



Implement a `FolderWatcher` class wrapping watchdog's `Observer` and a custom `FileSystemEventHandler`. On detecting a `FileCreatedEvent` or `FileMovedEvent`, add the file path to an internal processing queue (use `queue.Queue` for thread safety). Filter events to ignore the `done/` and `failed/` subdirectories.



The watcher should:

1\. On startup, scan the watch folder for pre-existing files and enqueue them

2\. Deduplicate events (watchdog may fire multiple events for a single file)

3\. Ignore temporary files (patterns: `\\\*.tmp`, `\\\*.part`, `~\\\*`, `.\\\*`)



\### filestate.py



Implement `wait\\\_for\\\_stable(filepath, interval, max\\\_wait)` — a function that polls a file's size and modification time until they remain unchanged across two consecutive checks. This prevents processing files still being written. Return `True` when stable, `False` if max\_wait exceeded.



Also implement `move\\\_to\\\_folder(filepath, destination\\\_folder)` handling filename collisions by appending a timestamp suffix if necessary.



\### executor.py



Implement `run\\\_script(script\\\_path, file\\\_path, timeout)` using `subprocess.run()`. Capture stdout and stderr for logging. Return a result object containing: exit\_code, stdout, stderr, duration. Handle `subprocess.TimeoutExpired` by killing the process tree and treating it as a failure.



The executor must work cross-platform: on Windows, avoid shell=True; on Linux, consider using `start\\\_new\\\_session=True` to enable clean process group termination.



\### config.py



Define a `Config` dataclass consolidating all settings. Implement a loader that merges (in priority order): defaults → config file → environment variables (prefixed `QUEUEDIR\\\_`) → CLI arguments.



\### \_\_main\_\_.py



Wire everything together:

1\. Parse CLI and load config

2\. Create done/failed directories if they don't exist

3\. Initialize watcher and start observer thread

4\. In main loop: pull file from queue, wait for stability, execute script, move file based on result

5\. Handle SIGINT/SIGTERM for graceful shutdown (finish current job, then exit)



\## Logging



Use Python's `logging` module. Default level INFO, showing: file detected, processing started, result (success/failure with exit code), file moved. At DEBUG level, include stdout/stderr from scripts and stability check details.



\## Testing Strategy



Unit tests for each module using pytest. For watcher tests, use a temporary directory and actually create/move files. For executor tests, create simple shell scripts (bash on Linux, batch on Windows) that exit with known codes. Integration test: end-to-end scenario with a mock script that writes output, verifying the file moves correctly.



Use `pytest-timeout` to prevent hanging tests. Target 90%+ coverage on core modules.



\## Installation and Usage



Distribute via PyPI. After `pip install queuedir`, usage:



```

queuedir --watch /path/to/inbox --script /path/to/process.sh

```



Also support running as a module: `python -m queuedir ...`



\## Future Considerations (Out of Scope for v1)



\- Parallel processing with configurable worker count

\- Retry logic with exponential backoff for failed files

\- Web UI or REST API for queue inspection

\- Systemd/Windows Service integration helpers

\- File filtering by extension or glob pattern



\## Success Criteria



The implementation is complete when: (1) a file dropped into the watched folder triggers script execution with that file as argument, (2) the file moves to done/ or failed/ based on exit code, (3) the system runs stably on both Windows and Linux, (4) graceful shutdown works, and (5) pre-existing files are processed on startup.

