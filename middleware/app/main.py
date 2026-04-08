"""
Main Server Application Module.
This module provisions the FastAPI framework heavily integrated with LangGraph and FAISS.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import chat, documents
from app.core.config import settings

# Explicitly configure Swagger UI (docs) and ReDoc
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Mossy Chatbot API utilizing LangGraph Agents and OpenWebUI.",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",      # Swagger UI endpoint
    redoc_url="/redoc"     # ReDoc endpoint
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router mimicking OpenAI format that OpenWebUI expects
app.include_router(chat.router, prefix=settings.API_V1_STR, tags=["chat"])
# Include the RAG and database ingestion endpoints
app.include_router(documents.router, prefix=settings.API_V1_STR, tags=["documents"])

@app.get("/health")
def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
