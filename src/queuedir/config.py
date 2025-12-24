import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    watch_dir: Path
    script_path: Path
    done_dir: Optional[Path] = None
    failed_dir: Optional[Path] = None
    timeout: int = 1200
    poll_interval: float = 2.0
    venv_path: Optional[Path] = None
    once: bool = False
    verbose: bool = False

    def __post_init__(self):
        self.watch_dir = Path(self.watch_dir).resolve()
        self.script_path = Path(self.script_path).resolve()
        if self.done_dir is None:
            self.done_dir = self.watch_dir / "done"
        else:
            self.done_dir = Path(self.done_dir).resolve()
        if self.failed_dir is None:
            self.failed_dir = self.watch_dir / "failed"
        else:
            self.failed_dir = Path(self.failed_dir).resolve()
        if self.venv_path is not None:
            self.venv_path = Path(self.venv_path).resolve()


def load_config(
    watch_dir: str,
    script_path: str,
    done_dir: Optional[str] = None,
    failed_dir: Optional[str] = None,
    timeout: Optional[int] = None,
    poll_interval: Optional[float] = None,
    venv_path: Optional[str] = None,
    once: bool = False,
    verbose: bool = False,
) -> Config:
    env_timeout = os.environ.get("QUEUEDIR_TIMEOUT")
    env_poll = os.environ.get("QUEUEDIR_POLL_INTERVAL")
    env_verbose = os.environ.get("QUEUEDIR_VERBOSE")
    env_venv = os.environ.get("QUEUEDIR_VENV")

    final_timeout = timeout if timeout is not None else (int(env_timeout) if env_timeout else 1200)
    final_poll = poll_interval if poll_interval is not None else (float(env_poll) if env_poll else 2.0)
    final_verbose = verbose or (env_verbose and env_verbose.lower() in ("1", "true", "yes"))
    final_venv = venv_path if venv_path is not None else env_venv

    return Config(
        watch_dir=watch_dir,
        script_path=script_path,
        done_dir=done_dir,
        failed_dir=failed_dir,
        timeout=final_timeout,
        poll_interval=final_poll,
        venv_path=final_venv,
        once=once,
        verbose=final_verbose,
    )
