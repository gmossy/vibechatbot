import os
import sys
from typing import List

import logfire
from langchain_core.tools import BaseTool, Tool
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client

_SERVICES_DIR = os.path.dirname(os.path.abspath(__file__))


def _middleware_pythonpath_env() -> dict[str, str]:
    """Ensure subprocess MCP servers can import `app.*` when spawned from the middleware."""
    env = dict(os.environ)
    root = os.path.abspath(os.path.join(_SERVICES_DIR, "..", ".."))
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = root + (os.pathsep + prev if prev else "")
    return env


def _format_call_tool_result(result) -> str:
    """Turn MCP CallToolResult into a string for LangChain tools."""
    if result is None:
        return ""
    blocks = getattr(result, "content", None)
    if not blocks:
        return str(result)
    parts: list[str] = []
    for block in blocks:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
        else:
            parts.append(str(block))
    return "\n".join(parts) if parts else str(result)


class MCPService:
    """
    Connects to stdio or SSE MCP servers and maps discovered tools to LangChain tools.
    """

    def __init__(self, mode: str = "stdio", **kwargs):
        self.mode = mode
        self.config = kwargs
        self.tools: List[BaseTool] = []

    def _stdio_parameters(self) -> StdioServerParameters:
        return StdioServerParameters(
            command=self.config.get("command", sys.executable),
            args=self.config.get("args", []),
            env=self.config.get("env") or _middleware_pythonpath_env(),
        )

    def _client_context(self):
        if self.mode == "sse":
            return sse_client(self.config["url"])
        return stdio_client(self._stdio_parameters())

    async def fetch_tools(self) -> List[BaseTool]:
        with logfire.span("mcp_fetch_tools", mode=self.mode):
            try:
                async with self._client_context() as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        listed = await session.list_tools()
                        lc_tools: List[BaseTool] = []
                        for m_tool in listed.tools:

                            def make_wrapper(name: str):
                                async def mcp_tool_coroutine(**kwargs):
                                    async with self._client_context() as (r, w):
                                        async with ClientSession(r, w) as s:
                                            await s.initialize()
                                            out = await s.call_tool(
                                                name, arguments=dict(kwargs)
                                            )
                                            return _format_call_tool_result(out)

                                return mcp_tool_coroutine

                            lc_tools.append(
                                Tool(
                                    name=m_tool.name,
                                    description=m_tool.description or "Remote MCP tool",
                                    func=None,
                                    coroutine=make_wrapper(m_tool.name),
                                )
                            )
                        self.tools = lc_tools
                        logfire.info(
                            "Loaded MCP tools", mode=self.mode, count=len(lc_tools)
                        )
                        return lc_tools
            except Exception as e:
                logfire.error("MCP fetch failed", mode=self.mode, error=str(e))
                return []


doc_mcp_service = MCPService(
    mode="stdio",
    command=sys.executable,
    args=[os.path.join(_SERVICES_DIR, "mcp_doc_library.py")],
    env=_middleware_pythonpath_env(),
)

arango_mcp_service = MCPService(
    mode="stdio",
    command=sys.executable,
    args=[os.path.join(_SERVICES_DIR, "mcp_arango_jazz.py")],
    env=_middleware_pythonpath_env(),
)

opensearch_mcp_service = MCPService(
    mode="sse",
    url="http://opensearch-mcp:8001/sse",
)
