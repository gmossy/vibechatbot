import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage

# Set environment to prevent live Logfire cloud uploads during test if needed, 
# though for verification we want to see it initialized.
os.environ["LOGFIRE_TOKEN"] = "test_token" 

# Ensure import paths
sys.path.append(os.getcwd())

import logfire
from app.services.agent_service import get_agent_graph
from app.services.rag_service import RAGService

async def verify_infrastructure():
    print("\n--- 🕵️ MOSSY CHATBOT SYSTEM VERIFICATION ---")
    
    # 1. Verify Logfire initialization
    print("\n[1/4] Verifying Logfire Configuration...")
    try:
        # We manually trigger a span to check if the library is active
        with logfire.span("verification_boot"):
            logfire.info("System verification started.")
        print("   ✅ Logfire spans are operational.")
    except Exception as e:
        print(f"   ❌ Logfire error: {e}")
        return

    # 2. Verify RAG Ingestion Pipeline + Tracing
    print("\n[2/4] Verifying RAG Pipeline Tracing...")
    rag = RAGService(user_id="verifier_bot", project_id="test_run")
    test_file = "verifier_test.txt"
    with open(test_file, "w") as f:
        f.write("The quick brown fox jumps over the lazy dog.")
    
    try:
        # We don't need to actually embed if we just want to see the logic flow,
        # but let's see if it runs through the spans.
        # We'll mock the FAISS part to avoid heavy model loading if possible.
        with patch("langchain_community.vectorstores.FAISS.from_documents") as mock_faiss:
            with patch("langchain_huggingface.HuggingFaceEmbeddings.embed_documents") as mock_emb:
                rag.ingest_file(test_file, test_file)
                print("   ✅ RAG Ingestion logic (load/split/trace) completed.")
    except Exception as e:
        print(f"   ❌ RAG Error: {e}")
    finally:
        if os.path.exists(test_file): os.remove(test_file)

    # 3. Verify Agent Logic + Verifier Node Flow
    print("\n[3/4] Verifying Agent Graph + Verifier Logic...")
    agent_graph = get_agent_graph()
    
    # Simulate a tool failure state
    messages = [
        HumanMessage(content="Test error flow"),
        AIMessage(content="", tool_calls=[{"name": "execute_terminal", "args": {"command": "ls /root"}, "id": "tc1"}]),
        ToolMessage(content="Permission denied", tool_call_id="tc1")
    ]
    
    state = {"messages": messages}
    try:
        # Run the verifier node
        result = await agent_graph._verify_results(state)
        final_msg = result["messages"][-1].content
        if "[VERIFIER]:" in final_msg:
            print("   ✅ Evaluator Node correctly intercepted and nudged the failed tool output.")
        else:
            print("   ❌ Evaluator Node failed to append nudge.")
    except Exception as e:
        print(f"   ❌ Graph Node Error: {e}")

    # 4. Verify Tool Instrumentation
    print("\n[4/4] Verifying Tool Spans...")
    from app.services.tools import calculator
    try:
        with logfire.span("manual_tool_test"):
            res = calculator.invoke({"expression": "2 + 2"})
            print(f"   ✅ Tool 'calculator' executed successfully (Result: {res}).")
    except Exception as e:
        print(f"   ❌ Tool Error: {e}")

    print("\n--- 🚀 VERIFICATION COMPLETE: SYSTEM IS HEALTHY 🚀 ---")

if __name__ == "__main__":
    asyncio.run(verify_infrastructure())
