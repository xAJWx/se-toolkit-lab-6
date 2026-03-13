# Documentation Agent - Task 2

## Overview

The Documentation Agent is an LLM-powered CLI tool that can answer questions about the software engineering toolkit by reading the project wiki. It uses tool calling to navigate and read documentation files.

## Architecture

### Core Components

1. **Agentic Loop** (`run_agentic_loop`)
   - Iterative process: LLM → tool calls → execute → feed back → repeat
   - Maximum 10 iterations to prevent infinite loops
   - Tracks all tool calls in history

2. **Tool Implementations** (`Tools` class)
   - `list_files(path)`: Safely lists directory contents
   - `read_file(path)`: Safely reads file contents
   - Path validation prevents directory traversal attacks

3. **LLM Integration**
   - OpenAI-compatible API (Qwen Code API)
   - Function calling with tool definitions
   - System prompt guides the agent's strategy

4. **Security Layer**
   - Validates all paths against project root
   - Prevents `../` traversal attacks
   - File size limits (1MB)
   - Handles non-existent files gracefully

## Agentic Loop Flow
