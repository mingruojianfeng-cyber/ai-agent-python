# 用 Pydantic 参数模型让工具调用也具备输入校验和 JSON Schema 生成能力。
from pydantic import BaseModel, Field

# 统一走安全路径解析，不能直接把模型给出的文件名拼接到磁盘路径。
from app.tools.common import resolve_tool_path


class ReadFileArgs(BaseModel):
    """读取文件工具的入参。"""

    # min_length=1 在工具执行前拒绝空文件名。
    file_name: str = Field(min_length=1, description="要读取的文件名")


class WriteFileArgs(BaseModel):
    """写入文件工具的入参。"""

    file_name: str = Field(min_length=1, description="要写入的文件名")
    # content 不设最小长度，允许创建空文件这一合法业务场景。
    content: str = Field(description="要写入的 UTF-8 文本内容")


def read_file(args: ReadFileArgs) -> str:
    """读取 tmp/file 中的 UTF-8 文件。"""
    try:
        # 解析并验证路径，确保读取范围限制在 tmp/file。
        path = resolve_tool_path("file", args.file_name)
        # 显式 UTF-8 避免依赖操作系统默认编码。
        return path.read_text(encoding="utf-8")
    # OSError 覆盖文件 I/O 失败；ValueError 覆盖安全路径校验失败。
    except (OSError, ValueError) as exc:
        return f"读取文件失败：{exc}"


def write_file(args: WriteFileArgs) -> str:
    """将 UTF-8 文本写入 tmp/file。"""
    try:
        path = resolve_tool_path("file", args.file_name)
        # 自动创建类别目录；parents=True 同时创建缺失父目录，exist_ok=True 使重复调用安全。
        path.parent.mkdir(parents=True, exist_ok=True)
        # write_text 负责打开、写入和关闭文件，等价于 Java try-with-resources 的简写。
        path.write_text(args.content, encoding="utf-8")
        return f"文件写入成功：{path}"
    except (OSError, ValueError) as exc:
        return f"写入文件失败：{exc}"
