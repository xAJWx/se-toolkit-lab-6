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

## Testing Strategy

- Create regression test that runs agent.py as subprocess
- Test with simple questions
- Validate JSON output format
- Check that tool_calls is empty array
