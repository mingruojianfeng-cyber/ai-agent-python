import pytest
from pydantic import ValidationError

from app.tools.order import GetOrderStatusArgs, get_order_status
from app.tools.registry import (
    ToolNotFoundError,
    execute_tool,
    get_tool_definitions,
    get_tool_registry,
)
from app.tools.weather import GetWeatherArgs, get_weather


def test_get_order_status_returns_mock_status() -> None:
    result = get_order_status(GetOrderStatusArgs(order_id="ORDER-1001"))

    assert result == "订单 ORDER-1001 当前状态：已发货，预计 2 天内送达。"


def test_get_order_status_rejects_empty_order_id() -> None:
    with pytest.raises(ValidationError):
        GetOrderStatusArgs(order_id="")


def test_get_weather_returns_mock_weather() -> None:
    result = get_weather(GetWeatherArgs(city="北京"))

    assert result == "北京 今日天气：晴，气温 18-26℃，适合出行。"


def test_get_weather_rejects_empty_city() -> None:
    with pytest.raises(ValidationError):
        GetWeatherArgs(city="")


def test_tool_registry_contains_order_and_weather_tools() -> None:
    registry = get_tool_registry()

    assert set(registry) == {"get_order_status", "get_weather"}
    assert registry["get_order_status"].description == "查询订单当前状态"
    assert registry["get_weather"].description == "查询城市天气"


def test_get_tool_definitions_returns_openai_compatible_schema() -> None:
    definitions = get_tool_definitions()

    assert definitions == [
        {
            "type": "function",
            "function": {
                "name": "get_order_status",
                "description": "查询订单当前状态",
                "parameters": {
                    "properties": {
                        "order_id": {
                            "description": "订单编号",
                            "minLength": 1,
                            "title": "Order Id",
                            "type": "string",
                        }
                    },
                    "required": ["order_id"],
                    "title": "GetOrderStatusArgs",
                    "type": "object",
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "查询城市天气",
                "parameters": {
                    "properties": {
                        "city": {
                            "description": "城市名称",
                            "minLength": 1,
                            "title": "City",
                            "type": "string",
                        }
                    },
                    "required": ["city"],
                    "title": "GetWeatherArgs",
                    "type": "object",
                },
            },
        },
    ]


def test_execute_tool_validates_arguments_and_dispatches_function() -> None:
    result = execute_tool("get_order_status", {"order_id": "ORDER-1002"})

    assert result == "订单 ORDER-1002 当前状态：已发货，预计 2 天内送达。"


def test_execute_tool_rejects_unknown_tool_name() -> None:
    with pytest.raises(ToolNotFoundError):
        execute_tool("unknown_tool", {})
