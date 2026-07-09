from pydantic import BaseModel, Field


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
    chat_id: str = "default"


class ChatResponse(BaseModel):
    """Response DTO for POST /chat, similar to a Java response record."""

    answer: str
