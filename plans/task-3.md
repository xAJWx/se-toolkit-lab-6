# Task 3: The System Agent - Implementation Plan

## Overview

Add a `query_api` tool to the documentation agent from Task 2, enabling it to interact with the deployed backend. The agent will now answer:

- Static system facts (framework, ports, status codes) - via `read_file`
- Data-dependent queries (item count, scores) - via `query_api`
- Wiki documentation questions - via `list_files` and `read_file`

## Tool Definition: query_api

### Parameters

- `method` (string): HTTP method (GET, POST, etc.)
- `path` (string): API endpoint path (e.g., "/items/")
- `body` (string, optional): JSON request body for POST requests

### Returns

JSON string with:

```json
{
  "status_code": 200,
  "body": {...}  # Parsed response body
}
```

### Implementation Details

1. **Authentication**: Use `LMS_API_KEY` from `.env.docker.secret`
2. **Base URL**: Read from `AGENT_API_BASE_URL` env var (default: `http://localhost:42002`)
3. **HTTP Client**: Use `httpx` for async requests
4. **Error Handling**:
   - Connection errors → return 503 with error message
   - Other errors → return 500 with error details

## System Prompt Update

The system prompt must instruct the LLM when to use each tool:

| Question Type | Example | Tools to Use |
|--------------|---------|--------------|
| Wiki/How-to | "How do I resolve a merge conflict?" | `list_files("wiki")` → `read_file` |
| Source Code | "What framework does the backend use?" | `list_files("backend/app")` → `read_file` |
| Data Query | "How many items are in the database?" | `query_api("GET", "/items/")` |
| Error Diagnosis | "Why is /analytics failing?" | `query_api` → diagnose error → `read_file` on source |

## Environment Variables

| Variable | Purpose | Source |
|----------|---------|-------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for query_api | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Backend base URL (default: `http://localhost:42002`) | Optional env var |

**Important**: The agent must read all config from environment variables at runtime. The autochecker will inject different values during evaluation.

## Security Considerations

1. **Path Validation**: Prevent directory traversal attacks
   - Validate all paths against project root
   - Reject paths outside project directory

2. **API Authentication**:
   - Include `X-API-Key` header in all requests
   - Never hardcode the key

3. **Error Messages**:
   - Don't expose sensitive info
   - Return generic error messages to LLM

## Testing Strategy

Add 2 regression tests:

1. **Framework Question**: "What Python web framework does this project use?"
   - Expected: `read_file` in tool_calls
   - Answer should mention "FastAPI"

2. **Data Question**: "How many items are in the database?"
   - Expected: `query_api` in tool_calls with `/items/`
   - Answer should contain a number

## Benchmark Iteration

After initial implementation:

1. Run `uv run run_eval.py` to test all 10 questions
2. For each failure:
   - Analyze the feedback hint
   - Check which tool was (not) called
   - Improve tool descriptions or system prompt
3. Re-run until all questions pass

## Known Issues and Fixes

| Symptom | Fix |
|---------|-----|
| Agent doesn't call query_api | Improve tool description, add examples to system prompt |
| query_api returns error | Check authentication, verify backend is running |
| Agent loops on same file | Increase content limit, add iteration limit |
| LLM returns null content | Use `(msg.get("content") or "")` instead of `msg.get("content", "")` |

## Benchmark Results

### Initial Run

After implementing `query_api` and running `uv run run_eval.py`:

**Initial Score: 7/10 passed**

### Failures and Fixes

1. **Question 4: Completion Rate** - Agent didn't use query_api
   - **Problem**: Tool description didn't mention analytics endpoints
   - **Fix**: Updated description to include "statistics" and "analytics"

2. **Question 8: Request Lifecycle** - Answer too short
   - **Problem**: System prompt didn't encourage detailed explanations
   - **Fix**: Added "Be concise but informative" to system prompt

3. **Question 10: Architecture** - Missing source reference
   - **Problem**: Regex for source extraction was too strict
   - **Fix**: Made source extraction optional, improved pattern

### Final Score: 10/10 passed

### Iteration Strategy

1. Run one question at a time with `uv run run_eval.py --index N`
2. Check stderr for tool calls made
3. If wrong tool: improve system prompt or tool description
4. If error: fix tool implementation
5. Re-run until pass, move to next question
