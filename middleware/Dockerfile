FROM python:3.13-slim

WORKDIR /app

# Install uv by copying it from the official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Tesseract for Image OCR capabilities
RUN apt-get update && apt-get install -y tesseract-ocr && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Use uv for incredibly fast installation directly into the system python paths
RUN uv pip install --system --no-cache -r requirements.txt

COPY . .

# Run the FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
