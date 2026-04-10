# 🤖 Mossy Chatbot (V2)
**Production-Grade Agentic RAG Pipeline with Docling & LangGraph**

**Author**: Glenn Mossy, AI and Machine Learning Engineer  
**Tech Stack**: Python 3.12+, FastAPI, LangGraph, Docling 2.x, FAISS, Ollama, Logfire

---

## 🌟 Executive Summary
Mossy Chatbot is a state-of-the-art Agentic Chat application built to operate locally and securely. It bridges the aesthetics of **OpenWebUI** with a sophisticated **LangGraph** Python architecture. 

It features an **Optimal RAG Pipeline** powered by **Docling 2.x**, enabling high-quality ingestion of multi-format documents (PDFs with OCR, Excel, Word, XML, Source Code) into a layout-aware **FAISS Vector Engine**.

---

## 🚀 Quick Start (Clone & Run)

### 1. Clone the Repository
```bash
git clone https://github.com/gmossy/mossychatbot.git
cd mossychatbot
```

### 2. Configure the Environment
Create a `.env` file in the root directory. You can copy the template:
```bash
cp middleware/.env.example .env
```

**Required Parameters:**
- `HF_TOKEN`: Your HuggingFace Token (required for embedding models).
- `LOGFIRE_TOKEN`: (Optional) Your Logfire project token for distributed tracing.
- `OLLAMA_BASE_URL`: Defaults to `http://ollama:11434` for Docker, or `http://localhost:11434` for local dev.

### 3. Build & Run (Docker)
The project is fully orchestrated via a centralized `Makefile`:

```bash
# Build the images (no-cache to ensure latest Docling/dependencies)
make build

# Start the full stack (OpenWebUI + Middleware + Ollama)
make up

# Watch the logs
make logs
```

---

## 🔧 Environment & Observability (Logfire)

This project uses **Logfire** for deep observability and distributed tracing across the agentic loop.

- **To enable Logfire**: Set `LOGFIRE_TOKEN` in your `.env`.
- **To change the project name**: Update `LOGFIRE_PROJECT_NAME`.
- **Legacy Formats**: The RAG pipeline automatically detects legacy binary formats (`.doc`, `.xls`) and logs a warning with a "How to fix" hint in Logfire while providing a clear error message to the user.

---

## 🧠 Changing LLM Models

The chatbot defaults to **Gemma 2**. You can swap models easily:

1. **Via UI**: In OpenWebUI, select the model from the dropdown. If a model isn't downloaded, the middleware will attempt to pull it automatically.
2. **Via Docker Compose**: Update the `DEFAULT_MODELS` environment variable in `docker-compose.yml`.
3. **Optimizing for Mac**: For 100% performance on Mac M-Series, run Ollama natively (`OLLAMA_HOST=0.0.0.0 ollama serve`) and update `OLLAMA_BASE_URL` in `.env` to `http://host.docker.internal:11434`.

---

## 🏗️ The RAG Pipeline (Docling Enhancements)

The `RAGService` has been modernised with **Docling 2.x**:
- **Structured Parsing**: Uses `DOC_CHUNKS` and `HybridChunker` (layout-aware) to ensure tables and semantic structures are preserved.
- **Multi-Format Support**:
    - **Native**: PDF (with OCR), DOCX, XLSX, PPTX, HTML, XML, CSV.
    - **Source Code**: Python, C++, C, CUE, Go, Rust, Java, etc.
    - **Images**: Native OCR via Docling IMAGE pipeline with Tesseract fallback.
- **Bulk Ingestion**: Supports automated ingestion of entire directories via `rag.bulk_ingest("/path/to/docs")` with graceful error skipping.

---

## 📡 Usage Commands

| Command | Action |
|:---|:---|
| `make up` | Start full docker stack |
| `make build` | Rebuild middleware with latest dependencies |
| `make run` | Run middleware locally for debugging |
| `make test` | Run diagnostic suite (RAG Stress, OCR, Dispatch) |
| `make clean` | Stop containers and clear all persistence volumes |

---

## 🧪 Testing
We maintain a robust suite of tests in `middleware/tests/`:
- `test_rag_dispatch.py`: Verifies optimal routing for all 15+ supported file formats.
- `test_pdf_quality.py`: Validates high-fidelity extraction from complex PDFs.
- `test_vision_ocr.py`: Ensures Tesseract fallback is functional for pure image files.
