import pytest
from contextlib import contextmanager
from app.agent import tools
import app.agent.tools as tools_module


class FakeCursor:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def execute(self, *args):
        pass
    def fetchone(self):
        return None


class FakeConnection:
    def cursor(self):
        return FakeCursor()


@contextmanager
def fake_connection():
    yield FakeConnection()


def test_read_file_rejects_traversal_and_absolute(tmp_path, monkeypatch):
    monkeypatch.setattr(tools_module.settings, "repo_root", tmp_path)
    monkeypatch.setattr(tools_module, "connection", fake_connection)
    with pytest.raises(ValueError):
        tools_module.read_file("../outside.ts", 1, 10)
    with pytest.raises(ValueError):
        tools_module.read_file(str(tmp_path / "src/app.ts"), 1, 10)


def test_read_file_rejects_unindexed(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/app.ts").write_text("hello")
    monkeypatch.setattr(tools_module.settings, "repo_root", tmp_path)
    monkeypatch.setattr(tools_module, "connection", fake_connection)
    with pytest.raises(ValueError, match="not indexed"):
        tools_module.read_file("src/app.ts", 1, 10)
