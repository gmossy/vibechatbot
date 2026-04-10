import time
import json
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.core.config import settings
from app.models.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionResponseChoice,
    MessageResponse
)
from app.services.agent_service import get_agent_graph

class LLMService:
    @staticmethod
    async def generate_response(request: ChatCompletionRequest, user_id: str = "default_user"):
        
        # Translate OpenWebUI / OpenAI dict messages to Langchain Core messages
        lc_messages = []
        for msg in request.messages:
            if msg.role == "user":
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                lc_messages.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                lc_messages.append(SystemMessage(content=msg.content))
                
        # Define the graph configuration strictly containing model metadata
        config = {
            "configurable": {
                "model": request.model,
                "temperature": request.temperature,
                "user_id": user_id,
                "thread_id": f"{user_id}_default",
                "project_id": "default_project"
            }
        }

        if request.stream:
            async def generate():
                agent_graph = get_agent_graph()
                # LangGraph exposes astream. This yields output events natively.
                # Mode="messages" gives us chunk by chunk token generation.
                async for msg, metadata in agent_graph.app.astream(
                    {"messages": lc_messages}, 
                    stream_mode="messages",
                    config=config
                ):
                    # We only want to stream back actual assistant content
                    if isinstance(msg, AIMessage) and msg.content:
                        chunk = {
                            "id": f"chatcmpl-{int(time.time())}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": request.model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": msg.content},
                                    "finish_reason": None
                                }
                            ]
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                
                # Signal completion
                final_chunk = {
                    "id": f"chatcmpl-{int(time.time())}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(generate(), media_type="text/event-stream")
            
        else:
            agent_graph = get_agent_graph()
            # Synchronous invocation
            final_state = await agent_graph.app.ainvoke({"messages": lc_messages}, config=config)
            
            # The final response is the last message appended to the state
            final_message = final_state["messages"][-1].content
            
            return ChatCompletionResponse(
                id=f"chatcmpl-{int(time.time())}",
                created=int(time.time()),
                model=request.model,
                choices=[
                    ChatCompletionResponseChoice(
                        index=0,
                        message=MessageResponse(
                            role="assistant", 
                            content=final_message
                        ),
                        finish_reason="stop"
                    )
                ]
            )
