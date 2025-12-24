import logging
import os
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


def run_script(script_path: Path, file_path: Path, timeout: int, venv_path: Optional[Path] = None) -> ExecutionResult:
    start = time.monotonic()
    kwargs = {
        "capture_output": True,
        "text": True,
        "timeout": timeout,
    }
    if sys.platform != "win32":
        kwargs["start_new_session"] = True

    # Set up environment with venv activation if specified
    env = None
    if venv_path:
        env = os.environ.copy()

        # Determine the bin directory based on platform
        if sys.platform == "win32":
            bin_dir = venv_path / "Scripts"
        else:
            bin_dir = venv_path / "bin"

        # Set VIRTUAL_ENV and update PATH
        env["VIRTUAL_ENV"] = str(venv_path)
        env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"

        # Unset PYTHONHOME if set (can interfere with venv)
        env.pop("PYTHONHOME", None)

        kwargs["env"] = env

    # On Windows, .py files must be run through the Python interpreter
    # If venv is specified, use the venv's Python interpreter
    if script_path.suffix.lower() == ".py":
        if venv_path:
            if sys.platform == "win32":
                python_exe = venv_path / "Scripts" / "python.exe"
            else:
                python_exe = venv_path / "bin" / "python"
            cmd = [str(python_exe), str(script_path), str(file_path)]
        else:
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
