import time
from pathlib import Path

import pytest

from queuedir.filestate import wait_for_stable, move_to_folder, get_file_state


class TestGetFileState:
    def test_existing_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        state = get_file_state(f)
        assert state is not None
        assert state[0] == 5

    def test_nonexistent_file(self, tmp_path):
        f = tmp_path / "missing.txt"
        assert get_file_state(f) is None


class TestWaitForStable:
    def test_stable_file(self, tmp_path):
        f = tmp_path / "stable.txt"
        f.write_text("content")
        assert wait_for_stable(f, interval=0.1, max_wait=2.0)

    def test_nonexistent_file(self, tmp_path):
        f = tmp_path / "missing.txt"
        assert not wait_for_stable(f, interval=0.1, max_wait=0.5)


class TestMoveToFolder:
    def test_basic_move(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("data")
        dest_dir = tmp_path / "dest"
        result = move_to_folder(src, dest_dir)
        assert result.exists()
        assert result.parent == dest_dir
        assert not src.exists()

    def test_collision_handling(self, tmp_path):
        src1 = tmp_path / "file.txt"
        src1.write_text("v1")
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        (dest_dir / "file.txt").write_text("existing")

        result = move_to_folder(src1, dest_dir)
        assert result.exists()
        assert result.name != "file.txt"
        assert "file_" in result.name
