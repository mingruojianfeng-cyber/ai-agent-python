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
        resolve_tmp_path("../../pyproject.toml")


def test_resolve_tool_path_rejects_category_link_to_outside_tmp(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.tools.common.TMP_ROOT", tmp_path)
    outside_directory = tmp_path.parent / "outside"
    outside_directory.mkdir()
    category_directory = tmp_path / "file"
    try:
        category_directory.symlink_to(outside_directory, target_is_directory=True)
    except OSError:
        pytest.skip("当前环境不允许创建符号链接")

    with pytest.raises(ValueError, match="路径不安全"):
        resolve_tool_path("file", "note.txt")


def test_resolve_tool_path_rejects_linked_tmp_root(tmp_path, monkeypatch) -> None:
    outside_directory = tmp_path.parent / "outside-root"
    outside_directory.mkdir()
    linked_root = tmp_path / "linked-tmp"
    try:
        linked_root.symlink_to(outside_directory, target_is_directory=True)
    except OSError:
        pytest.skip("当前环境不允许创建符号链接")
    monkeypatch.setattr("app.tools.common.TMP_ROOT", linked_root)

    with pytest.raises(ValueError, match="临时目录不安全"):
        resolve_tool_path("file", "note.txt")
