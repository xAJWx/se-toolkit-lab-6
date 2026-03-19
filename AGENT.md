# System Agent - Task 3

## Overview

The System Agent extends the Documentation Agent with a `query_api` tool, enabling it to interact with the deployed backend. It can now answer three categories of questions:

- **Wiki documentation** (procedures, how-to guides)
- **Static system facts** (framework, ports, status codes from source code)
- **Live data queries** (item counts, statistics via API)

This agent was built across three tasks:

- **Task 1**: Basic LLM integration with JSON output
- **Task 2**: Added file system tools (`list_files`, `read_file`) for documentation lookup
- **Task 3**: Added `query_api` tool for backend interaction

## Architecture

### Core Components

1. **Agentic Loop**
   - Iterative process with max 10 tool calls
   - Tracks all tool calls in history
   - Stops when LLM returns final answer without tool calls

2. **Tools**
   - `list_files(path)`: Explore directories
   - `read_file(path)`: Read files (wiki docs or source code)
   - `query_api(method, path, body)`: Query backend API

3. **LLM Integration**
   - OpenAI-compatible API (Qwen Code API)
   - Function calling with tool definitions
   - Enhanced system prompt for tool selection

4. **Security & Configuration**
   - Path validation prevents directory traversal
   - API authentication via `LMS_API_KEY`
   - All config from environment variables

### Data Flow

```
User Question
    ↓
Load Config (.env files)
    ↓
Agentic Loop (max 10 iterations)
    ├── Call LLM with tool definitions
    ├── LLM returns tool calls or final answer
    ├── Execute tools if needed
    └── Add results to messages
    ↓
Output JSON: {"answer": "...", "tool_calls": [...], "source": "..."}
```

## Tool Selection Strategy

The LLM is instructed to choose tools based on question type:

| Question Type | Example | Tools | Source Reference |
|--------------|---------|-------|------------------|
| Wiki/How-to | "How do I resolve a merge conflict?" | `list_files("wiki")` + `read_file` | wiki/git-workflow.md |
| Source Code | "What framework does the backend use?" | `list_files("backend")` + `read_file` | backend/app/main.py |
| Data Query | "How many items are in the database?" | `query_api("GET", "/items/")` | N/A (live data) |
| Error Diagnosis | "Why is /analytics failing?" | `query_api` then `read_file` on error | backend/app/*.py |

## Environment Variables

| Variable | Purpose | Required | Default |
|----------|---------|----------|---------|
| `LLM_API_KEY` | LLM provider API key | Yes | - |
| `LLM_API_BASE` | LLM API endpoint URL | Yes | - |
| `LLM_MODEL` | Model name | Yes | - |
| `LMS_API_KEY` | Backend API key for query_api | Yes | - |
| `AGENT_API_BASE_URL` | Backend base URL | No | `http://localhost:42002` |

**Important**: The agent never hardcodes these values. All are read from environment at runtime. The autochecker injects different values during evaluation.

## Tool Definitions

### query_api

The `query_api` tool allows the agent to query the backend API:

```python
{
    "type": "function",
    "function": {
        "name": "query_api",
        "description": "Query the backend API to get real data from the system. Use this for questions about counts, statistics, or current system state.",
        "parameters": {
            "type": "object",
            "properties": {
                "method": {"type": "string", "enum": ["GET", "POST"]},
                "path": {"type": "string", "description": "API endpoint path"},
                "body": {"type": "string", "description": "JSON request body for POST", "default": ""}
            },
            "required": ["method", "path"]
        }
    }
}
```

**Authentication**: The tool includes `X-API-Key` header with `LMS_API_KEY` value.

**Response Format**:

```json
{
    "status_code": 200,
    "body": {...}
}
```

## Usage

```bash
# Basic question
uv run agent.py "What is 2+2?"

# Wiki question
uv run agent.py "How do I resolve a merge conflict?"

# Source code question
uv run agent.py "What framework does the backend use?"

# Data question
uv run agent.py "How many items are in the database?"
```

## Output Format

The agent outputs JSON to stdout:

```json
{
  "answer": "The answer to the question",
  "source": "wiki/git-workflow.md",
  "tool_calls": [
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "file contents..."
    }
  ]
}
```

**Rules**:

- Only valid JSON goes to stdout
- All debug/progress output goes to stderr
- Exit code 0 on success
- Response within 60 seconds

## Benchmark Results

After implementing `query_api` and iterating on failures, the agent passes all 10 local benchmark questions:

| # | Question Type | Status |
|---|--------------|--------|
| 1 | Wiki: Branch protection | ✓ |
| 2 | Source: Framework | ✓ |
| 3 | Data: Item count | ✓ |
| 4 | Data: Completion rate | ✓ |
| 5 | Source: Port | ✓ |
| 6 | Source: Status code | ✓ |
| 7 | Error diagnosis | ✓ |
| 8 | Reasoning: Request lifecycle | ✓ |
| 9 | Multi-step: Bug fix | ✓ |
| 10 | Reasoning: Architecture | ✓ |

## Lessons Learned

1. **Tool descriptions matter**: The LLM relies heavily on tool descriptions to decide when to call them. Being explicit about use cases (e.g., "Use this for questions about counts") significantly improved tool selection.

2. **Handle null content**: When the LLM returns tool calls, the `content` field can be `null` (not missing). Using `msg.get("content") or ""` instead of `msg.get("content", "")` prevents `AttributeError`.

3. **Path validation is critical**: Security validation prevents the agent from reading files outside the project directory, protecting against path traversal attacks.

4. **Environment variable separation**: Keeping `LLM_API_KEY` (for the LLM provider) separate from `LMS_API_KEY` (for backend auth) avoids confusion and security issues.

5. **Iterative debugging**: Running `run_eval.py` and analyzing failures one at a time was more effective than trying to fix everything at once. The feedback hints guided improvements to the system prompt.

6. **Content truncation**: Large files can cause the LLM to miss information. The `read_file` tool limits files to 1MB, but the LLM context window also matters for very long files.

## Testing

### Task 1 Tests

- `test_agent_returns_valid_json`: Validates JSON output with required fields
- `test_agent_handles_missing_argument`: Checks error handling
- `test_agent_handles_long_question`: Tests with longer input

### Task 3 Tests

- `test_framework_question`: Verifies `read_file` usage for source questions
- `test_port_question`: Checks port detection
- `test_items_count_question`: Verifies `query_api` usage for data questions
- `test_status_code_question`: Tests HTTP status code knowledge
- `test_error_diagnosis_pattern`: Tests error analysis

## Future Improvements

1. **Caching**: Cache API responses to reduce redundant calls
2. **Parallel tool execution**: Execute independent tool calls in parallel
3. **Better error messages**: More descriptive errors for debugging
4. **Source extraction**: Automatically extract line numbers from source files
5. **Multi-modal support**: Add support for images and diagrams in wiki

## Files Structure

```
.
├── agent.py              # Main agent implementation
├── AGENT.md              # This documentation
├── plans/
│   ├── task-1.md         # Task 1 implementation plan
│   ├── task-2.md         # Task 2 implementation plan
│   └── task-3.md         # Task 3 implementation plan
├── tests/
│   ├── test_agent.py     # Task 1 tests
│   ├── test_documentation_agent.py  # Task 2 tests
│   └── test_system_agent.py  # Task 3 tests
├── .env.agent.secret     # LLM configuration
└── .env.docker.secret    # Backend configuration
```
