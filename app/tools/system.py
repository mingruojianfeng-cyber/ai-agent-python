from datetime import datetime

from pydantic import BaseModel, Field

from app.tools import common


ALLOWED_COMMANDS = {"dir", "ls", "pwd", "type", "Get-ChildItem"}
FORBIDDEN_TOKENS = ("|", ">", "<", "&", ";", "`", "$", "\n", "\r")


class NoArgs(BaseModel):
    """无入参工具的占位模型。"""


class TerminalCommandArgs(BaseModel):
    """受限终端工具的入参。"""

    command: str = Field(min_length=1, description="允许执行的只读命令")


def _list_directory(relative_path: str) -> str:
    path = common.resolve_tmp_path(relative_path)
    if not path.is_dir():
        return f"终端执行失败：不是目录：{relative_path}"
    return "\n".join(item.name for item in sorted(path.iterdir(), key=lambda item: item.name))


def execute_terminal_command(args: TerminalCommandArgs) -> str:
    """以 Python 内置操作执行 tmp 目录内的白名单只读命令。"""
    command_line = args.command.strip()
    if any(token in command_line for token in FORBIDDEN_TOKENS):
        return "不允许执行包含危险语法的命令"

    command, separator, relative_path = command_line.partition(" ")
    if command not in ALLOWED_COMMANDS:
        return f"不允许执行命令：{command}"

    relative_path = relative_path.strip() if separator else "."
    try:
        if command == "pwd":
            if separator:
                return "不允许为 pwd 提供参数"
            return str(common.TMP_ROOT)
        if command in {"dir", "ls", "Get-ChildItem"}:
            return _list_directory(relative_path)
        if not separator:
            return "不允许在未指定文件时执行 type"
        path = common.resolve_tmp_path(relative_path)
        if not path.is_file():
            return f"终端执行失败：不是文件：{relative_path}"
        return path.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        return f"终端执行失败：{exc}"


def terminate(args: NoArgs) -> str:
    """返回任务结束标记，供调用方决定如何结束交互。"""
    return "任务结束"


def get_current_time(args: NoArgs) -> str:
    """返回本地当前时间。"""
    return f"当前时间：{datetime.now().isoformat(timespec='seconds')}"
