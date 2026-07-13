import pytest

from app.tools.common import resolve_tmp_path, resolve_tool_path


def test_resolve_tool_path_uses_project_tmp_directory() -> None:
    path = resolve_tool_path("file", "note.txt")

    assert path.name == "note.txt"
    assert path.parent.name == "file"
    assert path.parents[1].name == "tmp"


@pytest.mark.parametrize("file_name", ["../secret.txt", "nested/file.txt", r"C:\\secret.txt"])
def test_resolve_tool_path_rejects_unsafe_file_name(file_name: str) -> None:
    with pytest.raises(ValueError, match="文件名不安全"):
        resolve_tool_path("file", file_name)


def test_resolve_tmp_path_rejects_parent_directory() -> None:
    with pytest.raises(ValueError, match="路径不安全"):
        resolve_tmp_path("../pyproject.toml")
