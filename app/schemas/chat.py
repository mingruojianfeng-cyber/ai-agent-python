from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000, description="The message to send to the chat model.")
    chat_id: str = "default"

class ChatResponse(BaseModel):
    answer: str