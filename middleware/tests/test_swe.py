import asyncio
from langchain_core.messages import HumanMessage
from app.services.agent_service import agent_graph

async def test_swe():
    print("--- 🛠 RUNNING SWE AGENT TEST 🛠 ---")
    query = "Write a python script called sweep.py that prints 'Hello from SWE test' and save it to the current directory. Execute it to verify."
    
    print(f"USER: {query}")
    inputs = {"messages": [HumanMessage(content=query)]}
    
    print("\n--- 🧠 AGENT REASONING STREAM ---")
    
    # We use stream to capture the thoughts, tool calls, and final messages
    final_response = ""
    async for event in agent_graph.app.astream(inputs, {"recursion_limit": 15}):
        for node_name, node_state in event.items():
            messages = node_state.get("messages", [])
            if messages:
                latest_msg = messages[-1]
                
                # If there are tool calls, print them!
                if hasattr(latest_msg, "tool_calls") and latest_msg.tool_calls:
                    print(f"[{node_name}] 🔧 Triggering Tools:")
                    for tc in latest_msg.tool_calls:
                        print(f"   -> {tc['name']}({tc['args']})")
                
                # Print the content
                if latest_msg.content:
                    print(f"\n[{node_name}] 🗣 {latest_msg.content[:500]}...")
                    final_response = latest_msg.content
                    
    print("\n--- ✅ FINAL AGENT OUTPUT ---")
    print(final_response)

if __name__ == '__main__':
    asyncio.run(test_swe())
