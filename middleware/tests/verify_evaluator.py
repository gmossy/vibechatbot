import asyncio
import os
import sys

# Ensure we can import from app
sys.path.append(os.path.join(os.getcwd(), ".."))

from app.services.agent_service import get_agent_graph
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage

async def test_verifier_node():
    print("\n--- 🧪 TESTING EVALUATOR/VERIFIER NODE ---")
    
    agent_graph = await get_agent_graph()
    
    # 1. Simulate a state where a tool has just failed
    messages = [
        HumanMessage(content="Read the file secret.txt"),
        AIMessage(content="", tool_calls=[{"name": "read_local_file", "args": {"filepath": "secret.txt"}, "id": "call_123"}]),
        ToolMessage(content="Error: File 'secret.txt' not found.", tool_call_id="call_123")
    ]
    
    print("\n[STEP 1] Injecting state with errored ToolMessage...")
    state = {"messages": messages}
    
    print("[STEP 2] Executing Verifier Node logic...")
    # config = {"configurable": {"thread_id": "test_thread", "user_id": "default_user", "project_id": "test_project"}}
    
    result = await agent_graph._verify_results(state)
    final_content = result["messages"][-1].content
    
    print(f"\n[RESULTS] Final Tool Output Content:\n\"{final_content}\"")
    
    if "[VERIFIER]:" in final_content:
        print("\n✅ SUCCESS: The Verifier node correctly detected the error and appended the correction nudge!")
    else:
        print("\n❌ FAILURE: The Verifier node did not append the nudge.")

if __name__ == "__main__":
    asyncio.run(test_verifier_node())
