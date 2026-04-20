from pathlib import Path

import pytest

from voice_agent.filesystem import FileAccessError, FilesystemContext
from voice_agent.tools import build_tools


def _tool_map(context: FilesystemContext):
    return {tool.name: tool for tool in build_tools(context)}


def test_change_directory_and_list_directory(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("hello", encoding="utf-8")
    context = FilesystemContext.from_values(tmp_path, [tmp_path])
    tools = _tool_map(context)

    result = tools["change_directory"].invoke({"path": "docs"})

    assert "Current directory changed" in result
    listing = tools["list_directory"].invoke({})
    assert "guide.md" in listing


def test_read_file_blocks_paths_outside_allowed_roots(tmp_path: Path):
    allowed = tmp_path / "allowed"
    blocked = tmp_path / "blocked"
    allowed.mkdir()
    blocked.mkdir()
    (blocked / "secret.txt").write_text("nope", encoding="utf-8")
    context = FilesystemContext.from_values(allowed, [allowed])
    tools = _tool_map(context)

    with pytest.raises(FileAccessError):
        tools["read_file"].invoke({"path": str(blocked / "secret.txt")})
