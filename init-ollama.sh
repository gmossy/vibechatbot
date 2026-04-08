#!/usr/bin/env bash
# Wait for ollama to be ready before pulling the model

echo "Waiting for ollama API to be up..."
until curl -s http://localhost:11434/api/tags > /dev/null; do
    sleep 2
done

echo "Ollama is ready. Pulling the Google Gemma model..."
# Since your Mac is M5 Pro Max with 48GB memory, using gemma:7b or gemma2:9b will easily fit and perform well.
docker exec -it mossy-ollama ollama pull gemma:7b
echo "Gemma model pulled successfully!"
