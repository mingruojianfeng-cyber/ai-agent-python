from app.tools.file_operations import ReadFileArgs, WriteFileArgs, read_file, write_file


def test_write_then_read_file_in_tmp(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.tools.common.TMP_ROOT", tmp_path)

    write_result = write_file(WriteFileArgs(file_name="note.txt", content="你好"))
    read_result = read_file(ReadFileArgs(file_name="note.txt"))

    assert "写入成功" in write_result
    assert read_result == "你好"
    assert (tmp_path / "file" / "note.txt").read_text(encoding="utf-8") == "你好"


def test_read_file_returns_error_for_missing_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.tools.common.TMP_ROOT", tmp_path)

    result = read_file(ReadFileArgs(file_name="missing.txt"))

    assert result.startswith("读取文件失败：")
