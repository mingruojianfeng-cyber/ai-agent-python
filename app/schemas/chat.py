from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Request DTO for POST /chat.

    For Java developers: this is similar to a Java request record plus Bean
    Validation annotations such as `@NotBlank` and `@Size`.
    """

    message: str = Field(
        min_length=1,
        max_length=1000,
        description="The message to send to the chat model.",
    )
    chat_id: str = Field(
        default="default",
        alias="chatId",
        description="Conversation id, equivalent to the Java chatId parameter.",
    )

    # Java 接口使用 chatId；Python 内部使用 chat_id。这个配置类似给 DTO 字段加 JSON 别名。
    model_config = ConfigDict(populate_by_name=True)


class ChatResponse(BaseModel):
    """Response DTO for POST /chat, similar to a Java response record."""

    answer: str
