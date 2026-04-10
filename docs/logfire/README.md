# Logfire Observability Guide

Logfire has been integrated into the Mossy Chatbot middleware to provide deep, structured observability into the agentic workflows, FastAPI endpoints, and Pydantic models.

## 🚀 Getting Started

### 1. Authentication
To view your project traces, you must authenticate with Logfire. Run the following in your middleware environment:

```bash
logfire auth
```

### 2. Live Dashboard
Once authenticated and the server is running, you can view the live dashboard at:
[https://logfire.pydantic.dev](https://logfire.pydantic.dev)

## 🔍 Instrumention Details

The current implementation covers the following:

- **FastAPI**: All incoming REST requests (OpenAI-compatible chat and RAG uploads) are automatically traced.
- **Agent Nodes**: The `reasoning_node` and `verifier_node` in LangGraph are wrapped in semantic spans.
- **Tools**: Every tool call (`calculator`, `web_search`, `execute_terminal`, etc.) is now a child span of the reasoning node, capturing input arguments and execution time.
- **RAG Pipeline**: Full tracing of the ingestion pipeline (`Docling` loading, chunking, and FAISS embedding) and retrieval latency.
- **Pydantic Validation**: Any data validation errors in our schemas (`app/models/schemas.py`) are captured with full context.

## 🏹 Tracing vs. Standard Logging

While standard Python `logging` (to stderr) is still available, **Logfire Tracing/Spans** are the preferred method for agentic observability for several reasons:

1.  **Hierarchy (Spans)**: Spans represent a period of time. When the agent calls a tool, the tool execution is shown AS A CHILD of the agent's thought process. This makes it easy to see exactly which "thought" triggered which "action."
2.  **Breadcrumbs**: Every decision (e.g., "Agent decided to call tools") is logged as an event within the current span, creating a perfect timeline of operations.
3.  **Performance Profiling**: Because each tool is wrapped in a span, you can see at a glance if a specific search or math operation is slowing down the entire chat response.
4.  **Error Propagation**: If a tool fails, the error is attached to the specific tool span, rather than getting lost in a flat text log.

## 🧪 Testing the Observability

To verify that Logfire is capturing data:

1. Start the server: `uvicorn app.main:app --reload`
2. Send a chat request from OpenWebUI.
3. Open the Logfire dashboard.
4. You should see a trace tree similar to this:
   - `chat_completions` (HTTP POST)
     - `reasoning_node` (Span)
       - `ChatOllama.ainvoke` (External Call)
     - `verifier_node` (Span)

## 🛠️ Advanced Debugging

If the Verifier node catches an error, it is explicitly logged to Logfire as an `info` event with the error content:

```python
logfire.info("Verifier detected anomaly: {content}", content=content)
```

Look for these events in the Logfire UI to debug why the agent might be failing specific tasks or tools.
