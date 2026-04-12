"""
Main Server Application Module.
This module provisions the FastAPI framework heavily integrated with LangGraph and FAISS.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import chat, documents, generated_files
from app.core.config import settings, build_cors_middleware_args
from app.services.agent_service import get_agent_graph
import logfire


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await get_agent_graph()
    except Exception as e:
        logfire.warn("Agent graph pre-warm failed", error=str(e))
    yield

# Initialize Logfire
logfire.configure(
    project_name=settings.LOGFIRE_PROJECT_NAME,
    token=settings.LOGFIRE_TOKEN
)
logfire.instrument_pydantic()

# Explicitly configure Swagger UI (docs) and ReDoc
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="OpenAI-compatible API for LangGraph agents, RAG, and OpenWebUI.",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",      # Swagger UI endpoint
    redoc_url="/redoc",    # ReDoc endpoint
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, **build_cors_middleware_args())

# Instrument FastAPI with Logfire for deep observability
logfire.instrument_fastapi(app)

# Include the router mimicking OpenAI format that OpenWebUI expects
app.include_router(chat.router, prefix=settings.API_V1_STR, tags=["chat"])
# Include the RAG and database ingestion endpoints
app.include_router(documents.router, prefix=settings.API_V1_STR, tags=["documents"])
app.include_router(generated_files.router, prefix=settings.API_V1_STR, tags=["generated_files"])

@app.get("/health")
def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
