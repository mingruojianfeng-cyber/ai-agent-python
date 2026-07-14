from app.tools.system import (
    NoArgs,
    TerminalCommandArgs,
    execute_terminal_command,
    get_current_time,
    terminate,
)


def test_terminal_rejects_shell_syntax() -> None:
    result = execute_terminal_command(TerminalCommandArgs(command="dir && whoami"))

    assert "不允许" in result


def test_terminal_lists_only_tmp_directory(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.tools.common.TMP_ROOT", tmp_path)
    (tmp_path / "visible.txt").write_text("ok", encoding="utf-8")

    result = execute_terminal_command(TerminalCommandArgs(command="dir"))

    assert "visible.txt" in result


def test_terminal_type_reads_file_within_tmp(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.tools.common.TMP_ROOT", tmp_path)
    (tmp_path / "note.txt").write_text("仅限临时目录", encoding="utf-8")

    result = execute_terminal_command(TerminalCommandArgs(command="type note.txt"))

    assert result == "仅限临时目录"


def test_terminal_rejects_unknown_command() -> None:
    result = execute_terminal_command(TerminalCommandArgs(command="whoami"))

    assert "不允许" in result


def test_terminate_returns_completion_marker() -> None:
    assert terminate(NoArgs()) == "任务结束"


def test_get_current_time_returns_current_time_text() -> None:
    assert get_current_time(NoArgs()).startswith("当前时间：")
