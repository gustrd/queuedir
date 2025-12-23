import time
from pathlib import Path

import pytest

from queuedir.watcher import FolderWatcher, should_ignore


class TestShouldIgnore:
    def test_ignores_tmp(self):
        assert should_ignore("file.tmp")

    def test_ignores_part(self):
        assert should_ignore("download.part")

    def test_ignores_tilde(self):
        assert should_ignore("~tempfile")

    def test_ignores_dotfiles(self):
        assert should_ignore(".hidden")

    def test_allows_normal(self):
        assert not should_ignore("document.pdf")
        assert not should_ignore("image.jpg")


class TestFolderWatcher:
    def test_scan_existing(self, tmp_path):
        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()
        done_dir = tmp_path / "done"
        failed_dir = tmp_path / "failed"

        (watch_dir / "file1.txt").write_text("a")
        (watch_dir / "file2.txt").write_text("b")
        (watch_dir / ".hidden").write_text("c")

        watcher = FolderWatcher(watch_dir, done_dir, failed_dir)
        watcher.scan_existing()

        assert watcher.file_queue.qsize() == 2

    def test_excludes_done_failed(self, tmp_path):
        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()
        done_dir = watch_dir / "done"
        done_dir.mkdir()
        failed_dir = watch_dir / "failed"
        failed_dir.mkdir()

        (watch_dir / "new.txt").write_text("a")
        (done_dir / "old.txt").write_text("b")

        watcher = FolderWatcher(watch_dir, done_dir, failed_dir)
        watcher.scan_existing()

        assert watcher.file_queue.qsize() == 1

    def test_get_file_timeout(self, tmp_path):
        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()
        done_dir = tmp_path / "done"
        failed_dir = tmp_path / "failed"

        watcher = FolderWatcher(watch_dir, done_dir, failed_dir)
        result = watcher.get_file(timeout=0.1)
        assert result is None

    def test_detects_new_file(self, tmp_path):
        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()
        done_dir = tmp_path / "done"
        failed_dir = tmp_path / "failed"

        watcher = FolderWatcher(watch_dir, done_dir, failed_dir)
        watcher.start()

        try:
            time.sleep(0.2)
            (watch_dir / "newfile.txt").write_text("content")
            time.sleep(0.5)

            result = watcher.get_file(timeout=1.0)
            assert result is not None
            assert result.name == "newfile.txt"
        finally:
            watcher.stop()
