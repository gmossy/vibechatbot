from typing import Annotated, Sequence, TypedDict, Literal
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_ollama.chat_models import ChatOllama
from langchain_core.runnables import RunnableConfig

from langgraph.checkpoint.memory import MemorySaver

from app.services.rag_service import RAGService
from app.services.tools import agent_tools
from app.core.config import settings
import logfire
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class AgentState(TypedDict):
    """The graph state tracking the conversation history natively."""
    messages: Annotated[Sequence[BaseMessage], add_messages]

class LangGraphAgent:
    def __init__(self):
        workflow = StateGraph(AgentState)
        tool_node = ToolNode(agent_tools)
        
        workflow.add_node("reasoning_agent", self._call_model)
        workflow.add_node("tools", tool_node)
        workflow.add_node("verifier", self._verify_results)
        
        workflow.add_edge(START, "reasoning_agent")
        workflow.add_conditional_edges("reasoning_agent", tools_condition)
        workflow.add_edge("tools", "verifier")
        workflow.add_edge("verifier", "reasoning_agent")
        
        # Configure scoped memory per physical LLM conversation thread
        self.checkpointer = MemorySaver()
        self.app = workflow.compile(checkpointer=self.checkpointer)
        
    async def _verify_results(self, state: AgentState):
        """
        Evaluator Node: Inspects the output of tool executions.
        If a critical error is detected (especially in terminal commands), 
        it can append a helpful hint for the reasoning agent to self-correct.
        """
        with logfire.span("verifier_node"):
            messages = state["messages"]
            last_msg = messages[-1]
            
            # We only care about verifying tool outputs (ToolMessages)
            if hasattr(last_msg, "tool_call_id"):
                content = last_msg.content.lower()
                error_keywords = ["error", "failed", "not found", "denied", "forbidden", "exception", "invalid"]
                if any(kw in content for kw in error_keywords):
                    logfire.info("Verifier detected anomaly: {content}", content=content)
                    # Append a small 'Verification System' nudge if things went wrong
                    nudge = (
                        "\n[VERIFIER]: I detected an error or failure in the previous tool output. "
                        "Analyze the error, correct your parameters or dependencies, and try again if necessary."
                    )
                    last_msg.content += nudge
                    
            return {"messages": messages}

    async def _call_model(self, state: AgentState, config: RunnableConfig = None):
        """
        Reasoning Node: The primary Brain of the agent.
        Uses Chain of Thought (CoT) to decide which tools to call.
        """
        with logfire.span("reasoning_node"):
            if config is None:
                config = {}
        
        # Thread constraints for isolation
        thread_id = config.get("configurable", {}).get("thread_id", "default_thread")
        user_id = config.get("configurable", {}).get("user_id", "default_user")
        project_id = config.get("configurable", {}).get("project_id", "default_project")
        messages = state["messages"]
        last_message = messages[-1].content if messages and hasattr(messages[-1], "content") else ""
        
        model_name = config.get("configurable", {}).get("model", "gemma4")
        temperature = config.get("configurable", {}).get("temperature", 0.7)
        
        llm = ChatOllama(
            model=model_name,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=temperature
        )
        
        # We explicitly bind the tools capability to the LLM here.
        # This tells Ollama what tools exist and passes JSON schemas.
        llm_with_tools = llm.bind_tools(agent_tools)
        
        # Dynamically load the FAISS store specific to this logical user and project
        rag_service = RAGService(user_id=user_id, project_id=project_id)
        context = rag_service.retrieve_context(last_message) if last_message else ""
        
        system_prompt = (
            "You are the Mossy Chatbot, an advanced autonomous Software Engineering (SWE) agent.\n"
            "You have access to a live Internet Web Search tool, a mathematical calculator, PDF/Word Document creators, and CRITICALLY: full native terminal and file system access.\n"
            "You can literally read, write, and execute Python code using `execute_terminal` and `write_local_file`.\n"
            "If the user asks you to write code, test code, or explore the environment: YOU MUST USE THE TERMINAL CALLS TO AUTONOMOUSLY DO IT!\n"
            "If the user asks for current, live internet information, YOU MUST execute a 'web_search' tool call.\n"
            "You MUST absolutely use Chain of Thought (CoT) reasoning. Before providing your final answer, "
            "think step-by-step. Wrap your internal logic and reasoning inside <thought>...</thought> tags.\n"
        )
        
        if context:
            system_prompt += f"\nHere is retrieved context from the user's RAG databases:\n{context}\n\n"
            
        sys_msg = SystemMessage(content=system_prompt)
        
        # Sliding Window Optimization: Keep only the most recent 20 messages to stay within the LLM context window.
        # This is the 'simplest' and most reliable approach for an open-source project.
        max_history = 20
        if len(messages) > max_history:
            logfire.info("Pruning history: trimming from {count} to {max}", count=len(messages), max=max_history)
            pruned_messages = list(messages)[-max_history:]
        else:
            pruned_messages = list(messages)

        logfire.info("Agent invoking LLM with {msg_count} messages", msg_count=len(pruned_messages))
        
        # Declarative retry logic for transient LLM/Ollama network issues
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            reraise=True
        )
        async def _invoke_with_retry():
            return await llm_with_tools.ainvoke([sys_msg] + pruned_messages)

        try:
            response = await _invoke_with_retry()
        except Exception as e:
            logfire.error("LLM Invocation critically failed after retries: {e}", e=e)
            raise e

        if response.tool_calls:
            logfire.info("Agent decided to call tools: {tools}", tools=[tc["name"] for tc in response.tool_calls])
        else:
            logfire.info("Agent providing final conversational response")
            
        return {"messages": [response]}

_AGENT_GRAPH_INSTANCE = None

def get_agent_graph():
    global _AGENT_GRAPH_INSTANCE
    if _AGENT_GRAPH_INSTANCE is None:
        _AGENT_GRAPH_INSTANCE = LangGraphAgent()
    return _AGENT_GRAPH_INSTANCE
