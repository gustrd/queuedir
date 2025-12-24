import subprocess
import sys
import pytest

from queuedir.config import Config
from queuedir.cli import process_file, run


@pytest.fixture
def success_script(tmp_path):
    script = tmp_path / "process.py"
    script.write_text("""
import sys
filepath = sys.argv[1]
with open(filepath) as f:
    content = f.read()
print(f"Processed: {content}")
sys.exit(0)
""")
    return script


@pytest.fixture
def fail_script(tmp_path):
    script = tmp_path / "fail.py"
    script.write_text('import sys; sys.exit(1)')
    return script


@pytest.fixture
def test_venv(tmp_path):
    """Create a test virtual environment."""
    venv_path = tmp_path / "test_venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
    return venv_path


class TestProcessFile:
    def test_success_moves_to_done(self, tmp_path, success_script):
        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()
        done_dir = tmp_path / "done"
        failed_dir = tmp_path / "failed"

        input_file = watch_dir / "input.txt"
        input_file.write_text("hello world")

        config = Config(
            watch_dir=watch_dir,
            script_path=success_script,
            done_dir=done_dir,
            failed_dir=failed_dir,
            timeout=30,
            poll_interval=0.1,
        )

        result = process_file(input_file, config)
        assert result is True
        assert not input_file.exists()
        assert (done_dir / "input.txt").exists()

    def test_failure_moves_to_failed(self, tmp_path, fail_script):
        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()
        done_dir = tmp_path / "done"
        failed_dir = tmp_path / "failed"

        input_file = watch_dir / "input.txt"
        input_file.write_text("data")

        config = Config(
            watch_dir=watch_dir,
            script_path=fail_script,
            done_dir=done_dir,
            failed_dir=failed_dir,
            timeout=30,
            poll_interval=0.1,
        )

        result = process_file(input_file, config)
        assert result is False
        assert not input_file.exists()
        assert (failed_dir / "input.txt").exists()


class TestRunOnce:
    def test_processes_existing_and_exits(self, tmp_path, success_script):
        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()
        done_dir = tmp_path / "done"
        failed_dir = tmp_path / "failed"

        (watch_dir / "a.txt").write_text("1")
        (watch_dir / "b.txt").write_text("2")

        config = Config(
            watch_dir=watch_dir,
            script_path=success_script,
            done_dir=done_dir,
            failed_dir=failed_dir,
            timeout=30,
            poll_interval=0.1,
            once=True,
        )

        run(config)

        assert (done_dir / "a.txt").exists()
        assert (done_dir / "b.txt").exists()
        assert not list(watch_dir.glob("*.txt"))


class TestVenvIntegration:
    def test_process_file_with_venv(self, tmp_path, test_venv):
        """Test that files are processed using the specified venv."""
        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()
        done_dir = tmp_path / "done"
        failed_dir = tmp_path / "failed"

        # Create a script that reports venv info
        venv_script = tmp_path / "venv_check.py"
        venv_script.write_text(f"""
import sys
import os
filepath = sys.argv[1]
# Write venv info to a marker file in a known location
marker = r"{tmp_path / "venv_marker.txt"}"
with open(marker, 'w') as f:
    f.write(f"{{os.environ.get('VIRTUAL_ENV', 'NONE')}}\\n")
    f.write(f"{{sys.executable}}\\n")
sys.exit(0)
""")

        input_file = watch_dir / "input.txt"
        input_file.write_text("test data")

        config = Config(
            watch_dir=watch_dir,
            script_path=venv_script,
            done_dir=done_dir,
            failed_dir=failed_dir,
            timeout=30,
            poll_interval=0.1,
            venv_path=test_venv,
        )

        result = process_file(input_file, config)
        assert result is True
        assert (done_dir / "input.txt").exists()

        # Check that the marker file was created with correct venv info
        marker_file = tmp_path / "venv_marker.txt"
        assert marker_file.exists()
        marker_content = marker_file.read_text()
        assert str(test_venv) in marker_content
