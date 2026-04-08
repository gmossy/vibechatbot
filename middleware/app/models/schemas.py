from pydantic import BaseModel, Field
from typing import List, Optional, Any, Union

class Message(BaseModel):
    role: str
    content: str
    
class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    
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
