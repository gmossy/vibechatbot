from fastapi import APIRouter
from typing import Dict, Any
from app.models.schemas import ChatCompletionRequest
from app.services.llm_service import LLMService
import time

router = APIRouter()

@router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    return await LLMService.generate_response(request)

@router.get("/models")
async def get_models() -> Dict[str, Any]:
    # Provide a stubbed list of models based on Gemma size suitable for MBP 48GB.
    return {
        "object": "list",
        "data": [
            {
                "id": "gemma:7b", 
                "object": "model", 
                "created": int(time.time()), 
                "owned_by": "google"
            },
            {
                "id": "gemma2:9b", 
                "object": "model", 
                "created": int(time.time()), 
                "owned_by": "google"
            }
        ]
    }
