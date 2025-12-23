import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    timed_out: bool = False


def run_script(script_path: Path, file_path: Path, timeout: int) -> ExecutionResult:
    start = time.monotonic()
    kwargs = {
        "capture_output": True,
        "text": True,
        "timeout": timeout,
    }
    if sys.platform != "win32":
        kwargs["start_new_session"] = True

    # On Windows, .py files must be run through the Python interpreter
    if script_path.suffix.lower() == ".py":
        cmd = [sys.executable, str(script_path), str(file_path)]
    else:
        cmd = [str(script_path), str(file_path)]

    try:
        result = subprocess.run(
            cmd,
            **kwargs,
        )
        duration = time.monotonic() - start
        return ExecutionResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            duration=duration,
        )
    except subprocess.TimeoutExpired as e:
        duration = time.monotonic() - start
        stdout = e.stdout if e.stdout else ""
        stderr = e.stderr if e.stderr else ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        logger.warning(f"Script timed out after {timeout}s for {file_path}")
        return ExecutionResult(
            exit_code=-1,
            stdout=stdout,
            stderr=stderr,
            duration=duration,
            timed_out=True,
        )
