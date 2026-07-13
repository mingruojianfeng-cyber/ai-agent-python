# TypeVar 让泛型函数在返回时保留调用方传入的目标类型信息。
from typing import TypeVar

# BaseModel 处理模型类；TypeAdapter 处理 list、dict 等非模型泛型。
from pydantic import BaseModel, TypeAdapter


# T 是“解析目标类型”的占位符，类似 Java 方法级泛型 <T>。
T = TypeVar("T")


def parse_structured_output(raw_content: str, output_type: type[T]) -> T:
    """把模型返回的 JSON 文本解析成指定结构。

    对象类型走 Pydantic Model；列表、集合、字典等类型走 TypeAdapter。
    这样后续 RAG 路由、工具参数、MCP 调用参数都可以复用同一套校验入口。
    """
    # Model 类型走 Pydantic 校验；其他泛型走 TypeAdapter，避免先得到 Any 再手工强转。
    # 先确认 output_type 确实是类，才能安全调用 issubclass，避免传入泛型时报 TypeError。
    if isinstance(output_type, type) and issubclass(output_type, BaseModel):
        # Pydantic 直接从 JSON 文本反序列化并执行字段校验。
        return output_type.model_validate_json(raw_content)

    # 对非 BaseModel 类型临时创建适配器，仍使用同一套 Pydantic 校验引擎。
    return TypeAdapter(output_type).validate_json(raw_content)
