import os
import subprocess
import sys
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


@pytest.fixture
def venv_info_script(tmp_path):
    """Script that prints venv information."""
    script = tmp_path / "venv_info.py"
    script.write_text('''import sys
import os
print(f"EXECUTABLE:{sys.executable}")
print(f"PREFIX:{sys.prefix}")
print(f"VIRTUAL_ENV:{os.environ.get('VIRTUAL_ENV', 'NOT_SET')}")
''')
    return script


@pytest.fixture
def test_venv(tmp_path):
    """Create a test virtual environment."""
    venv_path = tmp_path / "test_venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
    return venv_path


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

    def test_venv_activation(self, venv_info_script, test_venv, tmp_path):
        """Test that venv is properly activated when specified."""
        target = tmp_path / "input.txt"
        target.write_text("test")
        result = run_script(venv_info_script, target, timeout=10, venv_path=test_venv)

        assert result.exit_code == 0
        assert f"VIRTUAL_ENV:{test_venv}" in result.stdout
        # Check that the venv's Python is used (not the current interpreter)
        if sys.platform == "win32":
            expected_python = test_venv / "Scripts" / "python.exe"
        else:
            expected_python = test_venv / "bin" / "python"
        assert str(expected_python) in result.stdout
        assert str(test_venv) in result.stdout

    def test_no_venv_when_not_specified(self, venv_info_script, tmp_path):
        """Test that without venv, the current Python is used."""
        target = tmp_path / "input.txt"
        target.write_text("test")
        result = run_script(venv_info_script, target, timeout=10)

        assert result.exit_code == 0
        assert "VIRTUAL_ENV:NOT_SET" in result.stdout
        # Should use the current Python interpreter
        assert sys.executable in result.stdout
