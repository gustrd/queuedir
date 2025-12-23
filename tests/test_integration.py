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
