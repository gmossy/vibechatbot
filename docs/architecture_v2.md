# Mossy Chatbot Architecture V1.1

This document describes the current production architecture of the Mossy Chatbot as of April 2026.

## 🔗 Component Overview

The application is decomposed into three main layers:

1.  **Frontend (OpenWebUI)**:
    - A Next.js-based interface that provides a sleek, ChatGPT-like experience.
    - Connects to the Middleware via standard OpenAI-compatible REST APIs.
2.  **Middleware (FastAPI + LangGraph)**:
    - The core intelligence layer.
    - Handles authentication via **Keycloak**.
    - Orchestrates the **Evaluator-Optimizer** loop using LangGraph.
    - Manages long-term conversation memory using `MemorySaver`.
3.  **Engine Layer (Ollama + FAISS)**:
    - **Ollama**: Runs the **Gemma 4** model locally on Apple Silicon.
    - **FAISS**: Provides low-latency vector search for the RAG engine.
    - **PostgreSQL**: Stores Keycloak identity data and historical audit logs.

## 🔄 Data Flow

1.  **Ingestion**: Files (PDF, Word, Code) are uploaded to `/v1/upload`.
2.  **Vectorization**: The `RAGService` chunks the documents and indexes them in a FAISS store isolated by `user_id` and `project_id`.
3.  **Reasoning**: When a user chats, the `agent_service.py` compiles a LangGraph.
4.  **Looping**: The agent reasons, calls tools (e.g., terminal, search), and sends the output to a **Verifier Node**.
5.  **Streaming**: Once verified, the assistant response is streamed back to the UI.

## 🔒 Security Model

- **Authentication**: Keycloak brokers all identity. Every request must carry a valid JWT.
- **Isolation**: RAG data is physically segmented on disk: `/data/projects/{user_id}/{project_id}/`.
- **Resource Constraints**: Docker Compose limits are set on the middleware to prevent OOM errors on the host machine.
