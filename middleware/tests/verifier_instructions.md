# Verifier Node Testing Instructions

This guide explains how to verify the Evaluator-Optimizer loop (Verifier Node) within the Mossy Chatbot.

## 1. Automated Terminal Test
Run the pre-configured verification script from the `middleware` directory:

```bash
cd middleware
./.venv/bin/python3 tests/verify_evaluator.py
```

This script simulates a failed tool output and confirms that the Verifier node appends the appropriate correctional nudge to the graph state.

## 2. Manual UI Integration Test
To observe the agent's autonomous self-correction in the OpenWebUI frontend, use the following prompt:

> **"Read the content of the file `/tmp/mossy_hidden_key.txt`. If it doesn't exist, search the web to see if it's a common placeholder name."**

### Expected Behavior:
1. **Tool Invocation**: The agent calls `read_local_file`.
2. **Failure Capture**: The tool returns an error (file not found).
3. **Verification**: The Verifier node detects the "Error" keyword and appends:  
   `[VERIFIER]: I detected an error... Analyze the error and try again.`
4. **Autonomous Pivot**: The reasoning agent reads the Verifier's note and immediately switches to `web_search` to fulfill your secondary request, without requiring a manual "it failed" message from you.
