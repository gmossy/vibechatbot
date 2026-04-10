# Mossy Chatbot — Centralized Makefile
# Run all commands from the project root: /Users/glennmossy/chatbot

.PHONY: help up down build logs clean run test install

# Variables
MIDDLEWARE_DIR = middleware
IMAGE_NAME     = mossy-chatbot-middleware
PORT           = 8001

help:
	@echo ""
	@echo "Mossy Chatbot — Available Commands"
	@echo "-----------------------------------"
	@echo "  make up          Start full stack via Docker (OpenWebUI + Middleware + Ollama)"
	@echo "  make down        Stop all Docker containers"
	@echo "  make build       Rebuild the Docker images (no cache)"
	@echo "  make logs        Follow live container logs"
	@echo "  make run         Run middleware locally (no Docker)"
	@echo "  make install     Install Python dependencies locally"
	@echo "  make test        Run all diagnostic tests (RAG, OCR, Stress)"
	@echo "  make clean       Stop containers and remove volumes"
	@echo ""

# ─── Docker Commands ───────────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build --no-cache

logs:
	docker compose logs -f

clean:
	docker compose down -v
	rm -rf $(MIDDLEWARE_DIR)/temp_uploads/*
	rm -rf $(MIDDLEWARE_DIR)/data/*
	@echo "Cleanup complete."

# ─── Local Development Commands ────────────────────────────────
install:
	cd $(MIDDLEWARE_DIR) && uv pip install -r requirements.txt

run:
	cd $(MIDDLEWARE_DIR) && PYTHONPATH=. ./.venv/bin/python3 app/main.py

test:
	@echo "Running RAG Stress Test..."
	cd $(MIDDLEWARE_DIR) && PYTHONPATH=. ./.venv/bin/python3 tests/test_rag_stress.py
	@echo "Running Document Type Dispatch Test..."
	cd $(MIDDLEWARE_DIR) && PYTHONPATH=. ./.venv/bin/python3 tests/test_rag_dispatch.py
	@echo "Running Vision OCR Verification..."
	cd $(MIDDLEWARE_DIR) && eval "$$(/opt/homebrew/bin/brew shellenv)" && PYTHONPATH=. ./.venv/bin/python3 tests/test_vision_ocr.py
