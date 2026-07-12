from typing import TypeVar

from pydantic import BaseModel, TypeAdapter


T = TypeVar("T")


def parse_structured_output(raw_content: str, output_type: type[T]) -> T:
    """把模型返回的 JSON 文本解析成指定结构。

    对象类型走 Pydantic Model；列表、集合、字典等类型走 TypeAdapter。
    这样后续 RAG 路由、工具参数、MCP 调用参数都可以复用同一套校验入口。
    """
    # Model 类型走 Pydantic 校验；其他泛型走 TypeAdapter，避免先得到 Any 再手工强转。
    if isinstance(output_type, type) and issubclass(output_type, BaseModel):
        return output_type.model_validate_json(raw_content)

    return TypeAdapter(output_type).validate_json(raw_content)
