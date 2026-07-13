from pydantic import BaseModel, Field

from app.tools.common import resolve_tool_path


class ReadFileArgs(BaseModel):
    """读取文件工具的入参。"""

    file_name: str = Field(min_length=1, description="要读取的文件名")


class WriteFileArgs(BaseModel):
    """写入文件工具的入参。"""

    file_name: str = Field(min_length=1, description="要写入的文件名")
    content: str = Field(description="要写入的 UTF-8 文本内容")


def read_file(args: ReadFileArgs) -> str:
    """读取 tmp/file 中的 UTF-8 文件。"""
    try:
        path = resolve_tool_path("file", args.file_name)
        return path.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        return f"读取文件失败：{exc}"


def write_file(args: WriteFileArgs) -> str:
    """将 UTF-8 文本写入 tmp/file。"""
    try:
        path = resolve_tool_path("file", args.file_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args.content, encoding="utf-8")
        return f"文件写入成功：{path}"
    except (OSError, ValueError) as exc:
        return f"写入文件失败：{exc}"
