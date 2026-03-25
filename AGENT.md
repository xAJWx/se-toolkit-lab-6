# Agent Architecture

This document describes the architecture and implementation of the SE Toolkit Lab agent.

## Overview

The agent is a CLI tool that answers questions about the project by using an LLM with function calling capabilities. It has access to three tools that allow it to interact with the real world: reading files, listing directories, and querying the backend API.

## Architecture

### Components

1. **agent.py** - Main entry point that implements the agentic loop
2. **Tools** - Functions that the LLM can call to gather information
3. **System Prompt** - Instructions that guide the LLM's behavior
4. **Environment Configuration** - Credentials and settings loaded from `.env.agent.secret`

### Agentic Loop

The agent follows this loop:

1. Send the user's question + tool definitions to the LLM
2. If the LLM responds with `tool_calls`:
   - Execute each tool
   - Append results as `tool` role messages
   - Go back to step 1
3. If the LLM responds with a text message (no tool calls):
   - Extract the answer and source
   - Output JSON and exit
4. If 10 tool calls are reached, stop and return whatever answer is available

## Tools

### read_file

Reads a file from the project repository.

- **Parameters:** `path` (string) - Relative path from project root
- **Returns:** File contents as string, or error message
- **Security:** Prevents path traversal (no `../`)

### list_files

Lists files and directories at a given path.

- **Parameters:** `path` (string) - Relative directory path from project root
- **Returns:** Newline-separated listing of entries
- **Security:** Prevents path traversal

### query_api

Queries the backend API for data or system information.

- **Parameters:** 
  - `method` (string) - HTTP method (GET, POST, PUT, DELETE)
  - `path` (string) - API endpoint path
  - `body` (string, optional) - JSON request body
- **Returns:** JSON string with `status_code` and `body`
- **Authentication:** Uses `LMS_API_KEY` from environment in `Authorization: Bearer` header

## Environment Variables

The agent reads all configuration from environment variables:

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for `query_api` auth | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for `query_api` | Optional, defaults to `http://localhost:42002` |

## System Prompt Strategy

The system prompt guides the LLM to use the right tool for each type of question:

- **Wiki/documentation questions:** Use `list_files` to discover wiki files, then `read_file` to read the relevant file
- **Source code questions:** Use `list_files` to explore directories like `backend/app/routers`, then `read_file` to read specific files
- **Data queries:** Use `query_api` to query the backend API for items, analytics, etc.

The prompt emphasizes:
1. Thinking step by step
2. Using tools to gather information
3. Including source references in the answer
4. Being concise

## Decision Making: Wiki vs API Tools

The LLM decides which tool to use based on keywords in the question:

- **Wiki keywords:** "wiki", "documentation", "git workflow", "branch protection", "how to"
- **Source code keywords:** "backend", "routers", "modules", "API endpoints", "source code"
- **API keywords:** "database", "items", "analytics", "scores", "completion rate", "how many"

## Lessons Learned

### Challenge 1: Tool Message Ordering

Initially, the agent added tool results to messages before the assistant's tool call request. This caused the Qwen API to reject requests with the error "messages with role 'tool' must be a response to a preceeding message with tool_calls". 

**Solution:** Add the assistant message with tool_calls FIRST, then add tool results.

### Challenge 2: Path Handling

The agent initially used incorrect paths (e.g., "app" instead of "backend/app"). 

**Solution:** Updated the system prompt to emphasize using full paths relative to project root.

### Challenge 3: Source Extraction

The `extract_source` function initially only looked for wiki files in tool results.

**Solution:** Enhanced it to check:
1. `read_file` tool call arguments for wiki paths
2. Tool results for wiki file references
3. The answer itself for wiki path patterns

### Challenge 4: LLM Looping

The agent sometimes got stuck in loops, repeatedly calling the same tool.

**Solution:** 
- Limited to 10 iterations
- Improved system prompt to be more specific about when to stop
- Made tool descriptions more precise

## Final Evaluation Score

Local benchmark results: **8/10 passed (80%)** ✓

### Passed Questions:
1. ✓ Wiki question about branch protection
2. ✓ Wiki question about SSH connection
3. ✓ Source code question about web framework (FastAPI)
4. ✓ Source code question about API routers
5. ✓ Database query question (items count)
6. ✓ Authentication error question (401 status)
7. ✓ Bug diagnosis question (division by zero in completion-rate)
8. ✓ Multi-step debugging question (top-learners crash)

### Failed Questions:
9. ✗ Request journey question (requires reading multiple config files)
10. ✗ Completion rate edge case question (requires deep code analysis)

### Key Improvements Made:
1. Reduced max_iterations from 10 to 5 initially, then back to 10 for complex questions
2. Added `use_auth` parameter to `query_api` for testing unauthenticated access
3. Improved system prompt with explicit examples and stopping conditions
4. Added error handling to always return valid JSON
5. Enhanced `extract_source` to handle multiple file types

## Next Steps for Improvement

1. **Improve completion rate:** The agent sometimes stops mid-task. Adding better termination conditions would help.

2. **Optimize tool usage:** For questions about multiple files (like "list all routers"), the agent could read files in parallel or summarize more efficiently.

3. **Better error handling:** When the API returns unexpected data, the agent should adapt rather than getting stuck.

4. **Context management:** For long conversations, consider summarizing previous tool results to stay within token limits.

## Testing

Two regression tests are provided in `tests/test_agent_tools.py`:

1. `test_wiki_question_uses_read_file` - Verifies that wiki questions trigger `read_file` usage
2. `test_database_question_uses_query_api` - Verifies that data questions trigger `query_api` usage

Run tests with:
```bash
uv run python tests/test_agent_tools.py
```

## Usage

```bash
# Simple question
uv run agent.py "What is 2+2?"

# Wiki question
uv run agent.py "According to the project wiki, what steps are needed to protect a branch?"

# Data question
uv run agent.py "How many items are in the database?"

# Source code question
uv run agent.py "What Python web framework does the backend use?"
```

## Output Format

The agent outputs JSON with three fields:

```json
{
  "answer": "The answer to the question",
  "source": "wiki/github.md",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "file1.md\nfile2.md"
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/github.md"},
      "result": "File contents..."
    }
  ]
}
```
