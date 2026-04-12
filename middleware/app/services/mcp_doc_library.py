"""
MCP stdio server: exposes local FAISS/RAG search as MCP tools for the agent graph.
Run by the middleware via MCPService (subprocess); keep imports under `app.*`.
"""
from __future__ import annotations

import asyncio
import os
import sys

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

_MIDDLEWARE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _MIDDLEWARE_ROOT not in sys.path:
    sys.path.insert(0, _MIDDLEWARE_ROOT)

from app.services.rag_service import RAGService

app = Server("local-doc-rag", version="1.0.0")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="doc_rag_search",
            description=(
                "Search the local vector knowledge base (FAISS) for relevant chunks. "
                "Use doc_list_knowledge_bases if you need a valid project_id."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query.",
                    },
                    "project_id": {
                        "type": "string",
                        "description": "Knowledge base / project id.",
                        "default": "default_project",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User scope for stored indexes.",
                        "default": "default_user",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="doc_list_knowledge_bases",
            description="List available local knowledge bases (projects) for the given user scope.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User scope.",
                        "default": "default_user",
                    },
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    uid = arguments.get("user_id", "default_user")
    if name == "doc_rag_search":
        q = arguments.get("query", "")
        pid = arguments.get("project_id", "default_project")
        try:
            rag = RAGService(user_id=uid, project_id=pid)
            ctx = rag.retrieve_context(q)
            if not ctx:
                return [
                    types.TextContent(
                        type="text",
                        text=f"No relevant information found in project '{pid}'.",
                    )
                ]
            return [types.TextContent(type="text", text=ctx)]
        except Exception as e:
            return [types.TextContent(type="text", text=f"RAG error: {e}")]

    if name == "doc_list_knowledge_bases":
        try:
            projects = RAGService.list_available_projects(uid)
            if not projects:
                return [types.TextContent(type="text", text="No local knowledge bases found.")]
            lines = ["Available knowledge bases:"]
            for p_id, data in projects.items():
                desc = data.get("description", "")
                files = data.get("files", [])
                lines.append(f"- {p_id}: {desc} (files: {files})")
            return [types.TextContent(type="text", text="\n".join(lines))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {e}")]

    return [types.TextContent(type="text", text="Unknown tool")]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
