# System Agent - Task 3

## Overview

The System Agent extends the Documentation Agent with a `query_api` tool, enabling it to interact with the deployed backend. It can now answer three categories of questions:

- **Wiki documentation** (procedures, how-to guides)
- **Static system facts** (framework, ports, status codes from source code)
- **Live data queries** (item counts, statistics via API)

## Architecture

### Core Components

1. **Agentic Loop** (unchanged from Task 2)
   - Iterative process with max 10 tool calls
   - Tracks all tool calls in history

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

## Tool Selection Strategy

The LLM is instructed to choose tools based on question type:

| Question Type | Example | Tools |
|--------------|---------|-------|
| Wiki/How-to | "How do I resolve a merge conflict?" | `list_files("wiki")` + `read_file` |
| Source Code | "What framework does the backend use?" | `list_files("backend")` + `read_file` |
| Data Query | "How many items are in the database?" | `query_api("GET", "/items/")` |
| Error Diagnosis | "Why is /analytics failing?" | `query_api` then `read_file` on error |

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `LLM_API_KEY` | LLM provider API key | Yes |
| `LLM_API_BASE` | LLM API endpoint URL | Yes |
| `LLM_MODEL` | Model name | Yes |
| `LMS_API_KEY` | Backend API key for query_api | Yes |
| `AGENT_API_BASE_URL` | Backend base URL (default: <http://localhost:42002>) | No |

**Important**: The agent never hardcodes these values. All are read from environment at runtime.

## Benchmark Results

After implementing `query_api` and iterating on failures, the agent passes all 10 local benchmark questions:
