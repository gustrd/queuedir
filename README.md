# QueueDir

A lightweight, cross-platform folder-based job queue system. Monitors an input folder and executes a script for each file that appears.

## Installation

```bash
pip install queuedir
```

## Usage

```bash
queuedir --watch /path/to/inbox --script /path/to/process.sh
```

### Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--watch` | `-w` | Folder to monitor (required) | - |
| `--script` | `-s` | Script to execute (required) | - |
| `--done-dir` | | Destination for processed files | `{watch}/done` |
| `--failed-dir` | | Destination for failed files | `{watch}/failed` |
| `--timeout` | | Script timeout in seconds | 1200 |
| `--poll-interval` | | File stability check interval | 2 |
| `--venv` | | Path to virtual environment to activate | - |
| `--once` | | Process existing files and exit | - |
| `--verbose` | `-v` | Enable debug logging | - |

### Example

```bash
# Monitor inbox, run process.py for each file
queuedir -w ./inbox -s ./process.py -v

# Use a virtual environment for Python scripts
queuedir -w ./inbox -s ./process.py --venv /path/to/venv

# Process existing files once and exit
queuedir -w ./inbox -s ./process.sh --once
```

## How It Works

1. Files dropped into the watched folder are detected
2. QueueDir waits for the file to stabilize (no longer being written)
3. The configured script is executed with the file path as argument
4. On success (exit 0): file moves to `done/`
5. On failure (non-zero exit): file moves to `failed/`

## Virtual Environment Support

When you specify a virtual environment with `--venv`, QueueDir will:
- Set the `VIRTUAL_ENV` environment variable
- Add the venv's bin/Scripts directory to `PATH`
- Use the venv's Python interpreter for `.py` scripts
- Make all venv packages available to your scripts

You can also set the venv via the `QUEUEDIR_VENV` environment variable:
```bash
export QUEUEDIR_VENV=/path/to/venv
queuedir -w ./inbox -s ./process.py
```

## Script Requirements

Your script receives the file path as the first argument:

```bash
#!/bin/bash
filepath="$1"
echo "Processing: $filepath"
# ... do work ...
exit 0  # success
```

```python
#!/usr/bin/env python
import sys
filepath = sys.argv[1]
print(f"Processing: {filepath}")
# ... do work ...
sys.exit(0)  # success
```

## License

MIT
