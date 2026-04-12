from pydantic import BaseModel, Field
from typing import List, Optional, Any, Union

class Message(BaseModel):
    role: str = Field(..., description="The role of the message sender, usually 'user' or 'assistant'.")
    content: str = Field(..., description="The textual content of the message.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "role": "user",
                "content": "Hello! Can you help me analyze the documents I just uploaded?"
            }
        }
    }
    
class ChatCompletionRequest(BaseModel):
    model: str = Field(default="gemma4", description="The LLM model to use (e.g., gemma4, llama3).")
    messages: List[Message]
    stream: Optional[bool] = Field(default=False, description="Whether to stream the response as server-sent events.")
    temperature: Optional[float] = Field(default=0.7, description="Sampling temperature (0.0 to 1.0).")
    max_tokens: Optional[int] = Field(default=None, description="Maximum number of tokens to generate.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "model": "gemma4",
                "messages": [
                    {"role": "user", "content": "What is the primary objective of this repository?"}
                ],
                "stream": False,
                "temperature": 0.5
            }
        }
    }
    
class ChoiceDelta(BaseModel):
    content: Optional[str] = None
    role: Optional[str] = None

class ChunkChoice(BaseModel):
    index: int
    delta: ChoiceDelta
    finish_reason: Optional[str] = None
    
class ChatCompletionChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChunkChoice]

class MessageResponse(BaseModel):
    role: str
    content: str

class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: MessageResponse
    finish_reason: str

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionResponseChoice]
