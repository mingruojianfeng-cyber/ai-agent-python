# Any 用于表示 OpenAI tools 协议中的动态 JSON 字典。
from typing import Any

# LocalTool 将名称、描述、参数模型和执行函数绑定为一个工具定义对象。
from app.schemas.tool import LocalTool
from app.tools.file_operations import ReadFileArgs, WriteFileArgs, read_file, write_file
from app.tools.pdf_generation import GeneratePdfArgs, generate_pdf
from app.tools.system import (
    NoArgs,
    TerminalCommandArgs,
    execute_terminal_command,
    get_current_time,
    terminate,
)
from app.tools.web import (
    DownloadResourceArgs,
    ScrapeWebPageArgs,
    SearchWebArgs,
    download_resource,
    scrape_web_page,
    search_web,
)


class ToolNotFoundError(Exception):
    """请求执行未注册工具时抛出的业务异常。"""


def get_tool_registry() -> dict[str, LocalTool]:
    """集中注册从 Java 项目迁移的本地工具。"""
    # 列表是工具的单一注册源；每项将模型名称映射到参数 Schema 和本地实现。
    tools = [
        LocalTool(
            name="read_file",
            description="读取临时目录中的 UTF-8 文件内容",
            args_schema=ReadFileArgs,
            function=read_file,
        ),
        LocalTool(
            name="write_file",
            description="向临时目录写入 UTF-8 文件内容",
            args_schema=WriteFileArgs,
            function=write_file,
        ),
        LocalTool(
            name="generate_pdf",
            description="在临时目录中生成包含指定内容的 PDF 文件",
            args_schema=GeneratePdfArgs,
            function=generate_pdf,
        ),
        LocalTool(
            name="download_resource",
            description="下载 URL 资源到临时目录",
            args_schema=DownloadResourceArgs,
            function=download_resource,
        ),
        LocalTool(
            name="execute_terminal_command",
            description="执行受限的临时目录只读命令",
            args_schema=TerminalCommandArgs,
            function=execute_terminal_command,
        ),
        LocalTool(
            name="scrape_web_page",
            description="抓取网页并返回 HTML 内容",
            args_schema=ScrapeWebPageArgs,
            function=scrape_web_page,
        ),
        LocalTool(
            name="search_web",
            description="通过百度搜索引擎查询网页信息",
            args_schema=SearchWebArgs,
            function=search_web,
        ),
        LocalTool(
            name="terminate",
            description="在任务完成或无法继续时返回任务结束标记",
            args_schema=NoArgs,
            function=terminate,
        ),
        LocalTool(
            name="get_current_time",
            description="获取当前本地时间",
            args_schema=NoArgs,
            function=get_current_time,
        ),
    ]
    # 字典推导式以工具名建索引，使执行阶段可 O(1) 查找。
    return {tool.name: tool for tool in tools}


def get_tool_definitions() -> list[dict[str, Any]]:
    """获取可传给大模型的 OpenAI 兼容工具定义。"""
    # 列表推导式将所有本地定义转换成 OpenAI-compatible tools 数组。
    return [tool.to_openai_tool() for tool in get_tool_registry().values()]


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """根据工具名称校验入参并执行对应工具。"""
    # 每次执行重新取得注册表；它只创建轻量描述对象，不保存请求级状态。
    registry = get_tool_registry()
    # 未注册名称不能执行，避免模型任意调用模块中的其他函数。
    if name not in registry:
        raise ToolNotFoundError(f"未找到工具：{name}")

    # 取出已注册定义后，先通过其 args_schema 校验模型传来的 JSON 参数。
    tool = registry[name]
    # model_validate 执行类型转换和 Field 约束检查，失败会抛 ValidationError。
    args = tool.args_schema.model_validate(arguments)
    # 只有校验成功才调用真实函数，并将工具文本结果返回给上层 Agent。
    return tool.function(args)
