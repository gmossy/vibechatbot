import asyncio

import mcp.types as types
from arango import ArangoClient
from mcp.server import Server
from mcp.server.stdio import stdio_server

# ── ArangoDB Configuration ──────────────────────────────────────────────────
ARANGO_URL = "http://arangodb:8529"
DB_NAME = "jazz_vault"

app = Server("jazz-knowledge-graph", version="1.0.0")


def get_db():
    client = ArangoClient(hosts=ARANGO_URL)
    return client.db(DB_NAME, username="root", password="")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="query_jazz_aql",
            description="Execute a raw AQL query against the Jazz Knowledge Graph. Use this for complex relationship exploration.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The AQL query string."}
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_artist_details",
            description="Get info about a jazz musician and the songs they played on.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the artist (e.g. 'Miles Davis').",
                    }
                },
                "required": ["name"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    db = get_db()

    if name == "query_jazz_aql":
        try:
            cursor = db.aql.execute(arguments["query"])
            results = [doc for doc in cursor]
            return [types.TextContent(type="text", text=str(results))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"AQL Error: {str(e)}")]

    if name == "get_artist_details":
        artist_name = arguments["name"]
        try:
            aql = """
            FOR m IN Musicians
                FILTER m.name == @name
                LET songs = (
                    FOR s IN 1..1 OUTBOUND m plays_on
                    RETURN {title: s.title, album: s.album, year: s.year}
                )
                RETURN {artist: m, songs: songs}
            """
            cursor = db.aql.execute(aql, bind_vars={"name": artist_name})
            results = [doc for doc in cursor]
            return [types.TextContent(type="text", text=str(results))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    return [types.TextContent(type="text", text="Tool not found")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
