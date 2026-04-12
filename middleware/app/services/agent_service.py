import asyncio
from typing import Annotated, Sequence, TypedDict

import logfire
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama.chat_models import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.services.mcp_service import (
    arango_mcp_service,
    doc_mcp_service,
    opensearch_mcp_service,
)
from app.services.tools import agent_tools


class AgentState(TypedDict):
    """Graph state: conversation history."""

    messages: Annotated[Sequence[BaseMessage], add_messages]


class LangGraphAgent:
    def __init__(self, tools: list):
        self._tools = list(tools)
        logfire.info(
            "Agent tool registry",
            native_tools=len(agent_tools),
            total_tools=len(self._tools),
        )

        workflow = StateGraph(AgentState)
        tool_node = ToolNode(self._tools)

        workflow.add_node("reasoning_agent", self._call_model)
        workflow.add_node("tools", tool_node)
        workflow.add_node("verifier", self._verify_results)

        workflow.add_edge(START, "reasoning_agent")
        workflow.add_conditional_edges("reasoning_agent", tools_condition)
        workflow.add_edge("tools", "verifier")
        workflow.add_edge("verifier", "reasoning_agent")

        self.checkpointer = MemorySaver()
        self.app = workflow.compile(checkpointer=self.checkpointer)

    async def _verify_results(self, state: AgentState):
        """
        Evaluator node: if the last tool output looks like a failure, nudge the model.
        """
        with logfire.span("verifier_node"):
            messages = state["messages"]
            last_msg = messages[-1]

            if hasattr(last_msg, "tool_call_id"):
                content = last_msg.content.lower()
                error_keywords = [
                    "error",
                    "failed",
                    "not found",
                    "denied",
                    "forbidden",
                    "exception",
                    "invalid",
                ]
                if any(kw in content for kw in error_keywords):
                    logfire.info("Verifier detected anomaly: {content}", content=content)
                    nudge = (
                        "\n[VERIFIER]: I detected an error or failure in the previous tool output. "
                        "Analyze the error, correct your parameters or dependencies, and try again if necessary."
                    )
                    last_msg.content += nudge

            return {"messages": messages}

    async def _call_model(self, state: AgentState, config: RunnableConfig = None):
        """Reasoning node: bind tools and invoke the LLM."""
        with logfire.span("reasoning_node"):
            if config is None:
                config = {}

        messages = state["messages"]

        model_name = config.get("configurable", {}).get("model", "gemma4")
        temperature = config.get("configurable", {}).get("temperature", 0.7)

        llm = ChatOllama(
            model=model_name,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=temperature,
        )

        llm_with_tools = llm.bind_tools(self._tools)

        system_prompt = (
            "You are an advanced autonomous assistant running on the local agent stack.\n"
            "You have access to a live Web Search, PDF/Word creators, and native terminal/file system access.\n"
            "CRITICALLY: You have multiple local knowledge bases. If you don't know something, "
            "YOU MUST use 'discover_knowledge_bases' and then 'rag_search' to find the answer.\n"
            "Use Chain of Thought (CoT). Wrap your internal logic in <thought>...</thought> tags."
        )

        sys_msg = SystemMessage(content=system_prompt)

        max_history = 20
        if len(messages) > max_history:
            logfire.info(
                "Pruning history: trimming from {count} to {max}",
                count=len(messages),
                max=max_history,
            )
            pruned_messages = list(messages)[-max_history:]
        else:
            pruned_messages = list(messages)

        logfire.info(
            "Agent invoking LLM with {msg_count} messages", msg_count=len(pruned_messages)
        )

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            reraise=True,
        )
        async def _invoke_with_retry():
            return await llm_with_tools.ainvoke([sys_msg] + pruned_messages)

        try:
            response = await _invoke_with_retry()
        except Exception as e:
            logfire.error("LLM Invocation critically failed after retries: {e}", e=e)
            raise e

        if response.tool_calls:
            logfire.info(
                "Agent decided to call tools: {tools}",
                tools=[tc["name"] for tc in response.tool_calls],
            )
        else:
            logfire.info("Agent providing final conversational response")

        return {"messages": [response]}


_agent_instance: LangGraphAgent | None = None
_agent_lock = asyncio.Lock()


async def _build_tools_with_mcp() -> list:
    tools = agent_tools.copy()
    for service in (doc_mcp_service, arango_mcp_service, opensearch_mcp_service):
        try:
            mcp_tools = await service.fetch_tools()
            if mcp_tools:
                tools.extend(mcp_tools)
        except Exception as e:
            logfire.warn(
                "MCP service unreachable or misconfigured",
                error=str(e),
            )
    return tools


async def get_agent_graph() -> LangGraphAgent:
    """Lazy async singleton: MCP discovery runs in the current event loop (no asyncio.run)."""
    global _agent_instance
    if _agent_instance is not None:
        return _agent_instance
    async with _agent_lock:
        if _agent_instance is None:
            tools = await _build_tools_with_mcp()
            _agent_instance = LangGraphAgent(tools)
    return _agent_instance
