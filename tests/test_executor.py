import pytest

from queuedir.executor import run_script


@pytest.fixture
def success_script(tmp_path):
    script = tmp_path / "success.py"
    script.write_text('import sys; print("ok"); sys.exit(0)')
    return script


@pytest.fixture
def fail_script(tmp_path):
    script = tmp_path / "fail.py"
    script.write_text('import sys; print("error", file=sys.stderr); sys.exit(1)')
    return script


@pytest.fixture
def echo_script(tmp_path):
    script = tmp_path / "echo.py"
    script.write_text('import sys; print(sys.argv[1])')
    return script


class TestRunScript:
    def test_successful_execution(self, success_script, tmp_path):
        target = tmp_path / "input.txt"
        target.write_text("test")
        result = run_script(success_script, target, timeout=10)
        assert result.exit_code == 0
        assert "ok" in result.stdout
        assert not result.timed_out

    def test_failed_execution(self, fail_script, tmp_path):
        target = tmp_path / "input.txt"
        target.write_text("test")
        result = run_script(fail_script, target, timeout=10)
        assert result.exit_code == 1
        assert "error" in result.stderr
        assert not result.timed_out

    def test_script_receives_filepath(self, echo_script, tmp_path):
        target = tmp_path / "myfile.txt"
        target.write_text("content")
        result = run_script(echo_script, target, timeout=10)
        assert str(target) in result.stdout

    def test_result_has_duration(self, success_script, tmp_path):
        target = tmp_path / "input.txt"
        target.write_text("test")
        result = run_script(success_script, target, timeout=10)
        assert result.duration > 0
