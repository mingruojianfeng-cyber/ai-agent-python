# datetime 用于取得本机当前时间。
from datetime import datetime

from pydantic import BaseModel, Field

# 以模块形式导入公共路径工具，调用时保留 common 前缀以清楚表达来源。
from app.tools import common


# 工具并不启动 shell，而是只模拟这些只读命令的有限语义。
ALLOWED_COMMANDS = {"dir", "ls", "pwd", "type", "Get-ChildItem"}
# 这些 token 可用于管道、重定向、命令串联或命令替换，必须在解析前拒绝。
FORBIDDEN_TOKENS = ("|", ">", "<", "&", ";", "`", "$", "\n", "\r")


class NoArgs(BaseModel):
    """无入参工具的占位模型。"""


class TerminalCommandArgs(BaseModel):
    """受限终端工具的入参。"""

    command: str = Field(min_length=1, description="允许执行的只读命令")


def _list_directory(relative_path: str) -> str:
    # resolve_tmp_path 防止传入 ../ 离开 tmp 根目录。
    path = common.resolve_tmp_path(relative_path)
    if not path.is_dir():
        return f"终端执行失败：不是目录：{relative_path}"
    # 排序保证同一目录在不同文件系统上的输出稳定，join 将名称拼成多行文本。
    return "\n".join(item.name for item in sorted(path.iterdir(), key=lambda item: item.name))


def execute_terminal_command(args: TerminalCommandArgs) -> str:
    """以 Python 内置操作执行 tmp 目录内的白名单只读命令。"""
    # 去除首尾空白，避免空格干扰命令白名单判断。
    command_line = args.command.strip()
    if any(token in command_line for token in FORBIDDEN_TOKENS):
        return "不允许执行包含危险语法的命令"

    # partition 只切第一处空格，分别得到命令、分隔符和剩余路径。
    command, separator, relative_path = command_line.partition(" ")
    if command not in ALLOWED_COMMANDS:
        return f"不允许执行命令：{command}"

    # 未提供参数时默认指向 tmp 根目录；提供参数时再清除首尾空白。
    relative_path = relative_path.strip() if separator else "."
    try:
        # pwd 不接受路径参数，直接返回受限工作根目录而非实际进程目录。
        if command == "pwd":
            if separator:
                return "不允许为 pwd 提供参数"
            return str(common.TMP_ROOT)
        # 三个目录列举命令映射到同一个 Python 实现，避免真正执行 shell。
        if command in {"dir", "ls", "Get-ChildItem"}:
            return _list_directory(relative_path)
        if not separator:
            return "不允许在未指定文件时执行 type"
        # 剩余唯一命令 type 读取一个受安全限制的 UTF-8 文本文件。
        path = common.resolve_tmp_path(relative_path)
        if not path.is_file():
            return f"终端执行失败：不是文件：{relative_path}"
        # 显式编码保证输出不依赖 Windows 当前代码页。
        return path.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        return f"终端执行失败：{exc}"


def terminate(args: NoArgs) -> str:
    """返回任务结束标记，供调用方决定如何结束交互。"""
    # 此函数不终止 Python 进程，只返回可被 Agent 编排器识别的业务标记。
    return "任务结束"


def get_current_time(args: NoArgs) -> str:
    """返回本地当前时间。"""
    # isoformat 生成标准时间文本；timespec 限制到秒，避免展示无用微秒。
    return f"当前时间：{datetime.now().isoformat(timespec='seconds')}"
