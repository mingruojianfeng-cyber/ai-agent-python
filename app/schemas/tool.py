from collections.abc import Callable
from typing import Any

from pydantic import BaseModel


class LocalTool(BaseModel):
    """本地工具定义，类似 Java ToolCallback 的轻量版本。"""

    name: str
    description: str
    args_schema: type[BaseModel]
    function: Callable[[Any], str]

    model_config = {"arbitrary_types_allowed": True}

    def to_openai_tool(self) -> dict[str, Any]:
        """转换成 OpenAI-compatible tools 参数所需的 function schema。"""
        parameters = self.args_schema.model_json_schema()
        parameters.pop("description", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
            },
        }
