# Callable 描述函数签名，用于标注工具实际执行函数。
from collections.abc import Callable
# Any 表示工具参数和 OpenAI JSON 结构在静态类型层面不做进一步约束。
from typing import Any

from pydantic import BaseModel


class LocalTool(BaseModel):
    """本地工具定义，类似 Java ToolCallback 的轻量版本。"""

    # 前四个字段共同描述“模型可调用的一个本地函数”。
    name: str
    description: str
    args_schema: type[BaseModel]
    function: Callable[[Any], str]

    # 函数对象、类对象不是普通 JSON 值，需显式允许 Pydantic 保存它们。
    model_config = {"arbitrary_types_allowed": True}

    def to_openai_tool(self) -> dict[str, Any]:
        """转换成 OpenAI-compatible tools 参数所需的 function schema。"""
        # args_schema 保存的是“参数模型的类”，不是实例；调用类方法即可生成 JSON Schema。
        # 从参数 DTO 自动推导 JSON Schema，避免手写 schema 与校验规则不一致。
        parameters = self.args_schema.model_json_schema()
        # 顶层 description 对 function 参数 schema 无用；不存在时 None 避免抛 KeyError。
        parameters.pop("description", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
            },
        }
