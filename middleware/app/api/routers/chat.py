from fastapi import APIRouter, Depends
from typing import Dict, Any
from app.models.schemas import ChatCompletionRequest
from app.services.llm_service import LLMService
from app.core.security import get_current_user
import time

router = APIRouter()

@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    user_id: str = Depends(get_current_user)
):
    return await LLMService.generate_response(request, user_id=user_id)

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
