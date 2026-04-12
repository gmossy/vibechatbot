# Agentic AI Best Practices

This document outlines architectural principles and coding standards for this agent chatbot project, drawing from industry leaders such as Anthropic, Google DeepMind, and LangChain.

## 1. Architectural Philosophy: Workflows over Raw Agents

As highlighted in Anthropic's "Building Effective Agents," reliability stems from predictability.

- **Deterministic Workflows**: Use chains, routers, and parallel sections for tasks where the sequence is known.
- **Autonomous Agents**: Reservse cyclic reasoning loops for complex, non-deterministic engineering tasks where the path to a solution isn't fixed.
- **Micro-Agents**: Instead of one "God Agent," use specialized nodes (Reasoning, Verifying, Tool Execution) to maintain focused context.

## 2. The Evaluator-Optimizer Pattern

The "Agentic Loop" should always include a self-correction mechanism:
- **Verifier Nodes**: Every critical tool execution (like terminal commands or code generation) should be passed through a verifier node that checks for errors or hallucinations before the result is returned to the user.
- **Feedback Loops**: If a verifier fails, the agent should receive the error as context and be allowed 1-3 retries to correct course.

## 3. Structured I/O & Validation

- **Pydantic Everywhere**: Use Pydantic models for all data transfer objects (DTOs), tool arguments, and graph states.
- **Strict Typing**: Use Python type hints and `Annotated` types to ensure the LLM receives clear JSON schemas for tool calling.
- **Structured Extraction**: Prefer tools like `instructor` for extracting clean data from messy LLM responses.

## 4. Resilience & Retries (Tenacity)

Network calls to LLM providers (Ollama) or external search APIs (DuckDuckGo) are inherently transient.
- **Exponential Backoff**: Use `@retry` with `wait_exponential` to avoid overwhelming services during temporary outages.
- **Stop Conditions**: Always specify a `max_attempt` threshold (e.g., 3 attempts) to prevent infinite loops in the agentic graph.
- **Reraise Failure**: Ensure `reraise=True` is used so that the final failure is correctly propagated to the Verifier node or the error handling layer.

## 5. Observability & Debugging

- **Tracing**: Utilize tools like LangSmith or Logfire to visualize the execution graph and debug individual node latency.
- **Thread Isolation**: Use LangGraph `MemorySaver` to ensure user sessions are cryptographically and logically separated.
- **Logging**: Implement persistent logging for all terminal executions and file mutations to provide an audit trail.

## 5. Tool Safety & Sandboxing

- **Execute with Caution**: Tools like `execute_terminal` must be monitored. Future iterations should move terminal execution into ephemeral Docker containers or gVisor sandboxes to prevent host OS compromise.
- **Timeouts**: All tool calls must have strict timeouts (e.g., 30s) to prevent the agent from hanging on long-running processes.
