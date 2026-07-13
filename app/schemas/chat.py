# BaseModel 提供解析和校验；ConfigDict 配置模型；Field 描述单个字段约束。
from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """POST /chat 的请求 DTO，类似 Java record 加 @NotBlank、@Size 校验。"""

    # 注解 `str` 指定字段类型；Field 中的约束会在请求进入 Controller 前执行。
    message: str = Field(
        min_length=1,
        max_length=1000,
        description="The message to send to the chat model.",
    )
    # Python 内部遵循 snake_case，但 alias 允许 HTTP JSON 使用前端惯用的 chatId。
    chat_id: str = Field(
        default="default",
        alias="chatId",
        description="Conversation id, equivalent to the Java chatId parameter.",
    )

    # Java 接口使用 chatId；Python 内部使用 chat_id。这个配置类似给 DTO 字段加 JSON 别名。
    # 既接受 JSON 中的 chatId，也接受 Python 字段名 chat_id。
    model_config = ConfigDict(populate_by_name=True)


class ChatResponse(BaseModel):
    """POST /chat 的响应 DTO，类似只含 answer 字段的 Java response record。"""

    # 仅声明类型即可让 Pydantic 在构造和序列化时处理该响应字段。
    answer: str
