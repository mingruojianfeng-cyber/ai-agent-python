from typing import Any

from app.schemas.tool import LocalTool
from app.tools.order import GetOrderStatusArgs, get_order_status
from app.tools.weather import GetWeatherArgs, get_weather


class ToolNotFoundError(Exception):
    """请求执行未注册工具时抛出的业务异常。"""


def get_tool_registry() -> dict[str, LocalTool]:
    """集中注册本地工具，类似 Java 版 ToolRegistration。"""
    # 列表保留声明顺序，最终转换为字典后按工具名查找，类似 Spring 的 Bean 注册表。
    tools = [
        LocalTool(
            name="get_order_status",
            description="查询订单当前状态",
            args_schema=GetOrderStatusArgs,
            function=get_order_status,
        ),
        LocalTool(
            name="get_weather",
            description="查询城市天气",
            args_schema=GetWeatherArgs,
            function=get_weather,
        ),
    ]
    return {tool.name: tool for tool in tools}


def get_tool_definitions() -> list[dict[str, Any]]:
    """获取可传给大模型的工具定义列表。"""
    return [tool.to_openai_tool() for tool in get_tool_registry().values()]


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """根据工具名校验入参并执行工具。"""
    registry = get_tool_registry()
    if name not in registry:
        raise ToolNotFoundError(f"Tool not found: {name}")

    tool = registry[name]
    # 先把外部 JSON 校验并转换为 args_schema 实例，再交给真正的函数执行。
    args = tool.args_schema.model_validate(arguments)
    return tool.function(args)
