# ════════════════════════════════════════════════════════
#  Mossy Chatbot Middleware — Dockerfile
#  Base: python:3.12-slim (Debian Bookworm)
#  Build strategy: Layer-cached for fast rebuilds
# ════════════════════════════════════════════════════════

FROM python:3.12-slim

# ── Runtime Environment ───────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_SYSTEM_PYTHON=1 \
    DOCLING_ALLOW_EXTERNAL_PLUGINS=true

WORKDIR /app

# ── System Dependencies ───────────────────────────────────
# tesseract-ocr      : OCR engine for image ingestion (Tesseract fallback)
# libgl1             : OpenGL runtime required by some Docling/CV dependencies (Bookworm-compatible)
# libglib2.0-0       : GLib runtime for image processing libraries
# Note: libgl1-mesa-glx is deprecated in Debian Bookworm — use libgl1 instead
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ── Install uv (fast Python package manager) ─────────────
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# ── Layer-Cached Dependency Installation ─────────────────
# Copy requirements FIRST so Docker reuses this layer on code-only changes
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# ── Pre-bake ML Models ────────────────────────────────────
# Download embedding model at build time → instant startup, works offline
RUN python -c "\
from langchain_huggingface import HuggingFaceEmbeddings; \
HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2'); \
print('Embedding model cached.')"

# ── Application Code ──────────────────────────────────────
COPY . .

# ── Port ──────────────────────────────────────────────────
EXPOSE 8001

# ── Entrypoint ────────────────────────────────────────────
CMD ["python", "app/main.py"]
