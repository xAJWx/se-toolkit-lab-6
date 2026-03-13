# LLM Agent

## Overview

This agent is a CLI tool that connects to an LLM (Large Language Model) and returns structured JSON answers. It's the foundation for more complex agentic systems with tool calling.

## Architecture

### Components

1. **Configuration** - Loads from `.env.agent.secret`
2. **LLM Client** - Async HTTP client for API calls
3. **Response Parser** - Validates and formats responses

### LLM Provider: Qwen Code API

- **Provider**: Qwen Code API (hosted on VM)
- **Model**: `qwen3-coder-plus`
- **Why chosen**: Free (1000 requests/day), works from Russia, no credit card required, strong tool-calling support

## Usage

```bash
# Ask a question
uv run agent.py "What is the capital of France?"

# Output: {"answer": "Paris.", "tool_calls": []}
