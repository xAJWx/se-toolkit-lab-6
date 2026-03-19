# Task 1: Call an LLM from Code - Implementation Plan

## LLM Provider Choice

I will use **Qwen Code API** because:

- 1000 free requests per day
- Works from Russia without VPN
- No credit card required
- Strong tool-calling support for future tasks

## Model

- **Model**: qwen3-coder-plus
- **API Base**: http://<vm-ip>:<qwen-port>/v1
- **API Key**: Stored in .env.agent.secret

## Agent Structure

1. **Input**: Read question from command line argument
2. **Configuration**: Load LLM settings from .env.agent.secret
3. **API Call**: Send request to OpenAI-compatible endpoint
4. **Output**: Print JSON with required fields
5. **Error Handling**: Print debug info to stderr, exit with code 1 on error

## Implementation Details

- Use `httpx` for async HTTP requests
- Use `pydantic` for response validation
- Environment variables via `python-dotenv`
- Response format: `{"answer": "...", "tool_calls": []}`

## Code Structure

### Main Components

1. **Configuration Loading** (`load_config()`):
   - Reads `.env.agent.secret` and `.env.docker.secret`
   - Validates required environment variables
   - Returns `AgentConfig` pydantic model

2. **LLM Response Model** (`LLMResponse`):
   - `answer`: string - the LLM's answer
   - `tool_calls`: list - empty for task 1

3. **Main Function** (`main()`):
   - Parse command line arguments
   - Load configuration
   - Call LLM API
   - Output JSON to stdout

### Data Flow

```
User question (CLI arg) 
    → load_config() 
    → call_llm_with_tools() 
    → LLMResponse 
    → JSON to stdout
```

## Error Handling

- Missing env vars → ValueError with helpful message
- LLM API errors → print to stderr, exit code 1
- Invalid JSON output → caught by tests

## Testing Strategy

- Create regression test that runs agent.py as subprocess
- Test with simple questions
- Validate JSON output format
- Check that tool_calls is empty array
