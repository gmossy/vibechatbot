import os
import asyncio
from app.services.rag_service import rag_service
from app.services.tools import calculator, agent_tools, web_search

async def run_proof():
    print("\n--- 🤖 AGENT CHATBOT PROOF OF CONCEPT ---")
    
    # 1. Proving Tool Instantiation
    print("\n[✔] ALL AGENT TOOLS LOADED SUCCESSFULLY:")
    for tool in agent_tools:
        print(f"   - {tool.name}: {tool.description[:60]}...")
        
    print("\n[✔] TESTING CALCULATOR TOOL:")
    calc_res = calculator.invoke({"expression": "400 * 52"})
    print(f"   400 * 52 = {calc_res}")
    assert calc_res == "20800", "Calculator tool failed."

    # 2. Proving Web Search Tool
    print("\n[✔] TESTING DUCKDUCKGO WEB TOOL:")
    web_res = web_search.invoke({"query": "capital of France"})
    print(f"   Search Snippet: '{web_res[:100]}...'")
    assert len(web_res) > 0, "Web Search failed."
    
    # 3. Proving RAG PDF Extraction & Chunking
    print("\n[✔] TESTING RAG FAISS PIPELINE:")
    
    # Generate a mock text file
    test_file = "test_document.txt"
    with open(test_file, "w") as f:
        f.write("This open-source agent chatbot stack uses LangGraph and OpenWebUI. Example attribution line for RAG retrieval tests.")
        
    # Ingest directly into RAG!
    rag_service.ingest_file(test_file)
    print(f"   SUCCESS! File '{test_file}' intercepted, parsed, and embedded into FAISS Database.")
    
    # Verify retrieval
    context = rag_service.retrieve_context("What UI does this stack use?")
    print(f"   FAISS Retrieval Engine Yielded:\n   >> {context}\n")
    assert "OpenWebUI" in context, "FAISS failed to properly recall the embedded memory."
    
    # Clean up
    os.remove(test_file)
    
    print("--- 🚀 ALL MODULES TESTED AND OPERATIONAL 🚀 ---")

if __name__ == "__main__":
    asyncio.run(run_proof())
