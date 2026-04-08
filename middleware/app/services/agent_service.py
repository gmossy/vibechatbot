from typing import Annotated, Sequence, TypedDict, Literal
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_ollama.chat_models import ChatOllama

from app.services.rag_service import rag_service
from app.services.tools import agent_tools
from app.core.config import settings

class AgentState(TypedDict):
    """The graph state tracking the conversation history natively."""
    messages: Annotated[Sequence[BaseMessage], add_messages]

class LangGraphAgent:
    def __init__(self):
        workflow = StateGraph(AgentState)
        
        # Tools node utilizing our standard decorator tools
        tool_node = ToolNode(agent_tools)
        
        # We add the LLM node and the tools node
        workflow.add_node("reasoning_agent", self._call_model)
        workflow.add_node("tools", tool_node)
        
        # Entry point
        workflow.add_edge(START, "reasoning_agent")
        
        # Let langgraph automatically decide if tools were requested
        workflow.add_conditional_edges(
            "reasoning_agent",
            tools_condition,
        )
        
        # If it went to tools, execute them explicitly and then route back to the LLM to give the answer
        workflow.add_edge("tools", "reasoning_agent")
        
        self.app = workflow.compile()
        
    async def _call_model(self, state: AgentState, config: dict = None):
        if config is None:
            config = {}
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
        
        response = await llm_with_tools.ainvoke([sys_msg] + list(messages))
        
        return {"messages": [response]}

agent_graph = LangGraphAgent()
