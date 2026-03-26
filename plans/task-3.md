# Task 3 Plan: The System Agent

## Implementation Plan

### 1. Tool Schema: `query_api`

**Parameters:**
- `method` (string): HTTP method (GET, POST, PUT, DELETE, etc.)
- `path` (string): API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST/PUT requests

**Returns:** JSON string with:
- `status_code`: HTTP status code
- `body`: Response body as JSON object or string

**Authentication:** Use `LMS_API_KEY` from environment in `Authorization: Bearer <key>` header

### 2. Environment Variables

Read from environment (not hardcoded):
- `LLM_API_KEY`: LLM provider API key
- `LLM_API_BASE`: LLM API endpoint URL
- `LLM_MODEL`: Model name
- `LMS_API_KEY`: Backend API key for `query_api` auth
- `AGENT_API_BASE_URL`: Base URL for API (default: `http://localhost:42002`)

### 3. System Prompt Update

Update system prompt to explain when to use each tool:
- `read_file`: For reading source code files
- `list_files`: For discovering file structure
- `query_api`: For querying the deployed backend API (data queries, system facts)

### 4. Implementation Steps

1. Create `.env.agent.secret` with LLM configuration
2. Implement `query_api` tool function with:
   - HTTP request using `requests` library
   - Bearer token authentication
   - Error handling
3. Add tool schema to LLM function-calling definition
4. Update system prompt
5. Test with benchmark questions

### 5. Testing Strategy

Run `uv run run_eval.py` and iterate:
- Fix tool call issues
- Improve system prompt clarity
- Handle edge cases (errors, empty responses)

## Benchmark Results

### Final Results
- **Final score: 8/10 (80%)** ✓

### Passed Questions:
1. ✓ According to the project wiki, what steps are needed to protect a branch on GitHub?
2. ✓ What does the project wiki say about connecting to your VM via SSH?
3. ✓ What Python web framework does this project's backend use?
4. ✓ List all API router modules in the backend. What domain does each one handle?
5. ✓ How many items are currently stored in the database?
6. ✓ What HTTP status code does the API return when you request /items/ without authentication?
7. ✓ Query the /analytics/completion-rate endpoint for lab-99. What error do you get?
8. ✓ The /analytics/top-learners endpoint crashes for some labs. Find the error.

### Failed Questions:
9. ✗ Read docker-compose.yml and Dockerfile. Explain the HTTP request journey.
10. ✗ A learner completed lab-01 but completion rate shows 0%. Explain why.

### Iteration History

1. **Initial attempt:** 2-3/10 - Agent got stuck in exploration loops
2. **Reduced max_iterations to 5:** 3/10 - Faster but incomplete answers
3. **Improved system prompt with examples:** 5/10 - Better tool selection
4. **Added max_iterations=7 with final answer prompt:** 6/10 - Better completion
5. **Added use_auth parameter to query_api:** 7/10 - Can test unauthenticated access
6. **Increased max_iterations to 10:** 8/10 - Enough for complex multi-step questions

### Current Status

- ✓ `plans/task-3.md` exists with implementation plan
- ✓ `agent.py` defines `query_api` as function-calling schema
- ✓ `query_api` authenticates with `LMS_API_KEY`
- ✓ Agent reads LLM config from environment variables
- ✓ Agent reads `AGENT_API_BASE_URL` from environment
- ✓ Agent answers static system questions correctly
- ✓ Agent answers data-dependent questions
- ✓ `run_eval.py` passes 8/10 questions (80%)
- ✓ `AGENT.md` documents the architecture (400+ words)
- ✓ 2 tool-calling regression tests exist and pass

### Known Issues

1. **Agent doesn't stop after finding answer**: The LLM continues to explore directories even after finding the answer. This causes timeouts and incomplete answers.

2. **Inconsistent behavior**: The agent sometimes answers correctly, sometimes gets stuck in exploration loops. This may be due to:
   - LLM model limitations
   - System prompt needs more explicit stopping conditions
   - Token limits causing truncated responses

### Recommended Next Steps

1. **Try a different LLM model**: Qwen3-Coder-Plus may not be optimal for this task. Consider:
   - Using a more powerful model (if available)
   - Adjusting temperature and max_tokens parameters

2. **Improve stopping conditions**: Add more explicit instructions like:
   - "After reading ONE file that contains the answer, stop and provide the answer"
   - "Maximum 3 tool calls for simple questions"

3. **Simplify test questions**: The current benchmark may be too challenging. Consider:
   - Breaking complex questions into simpler ones
   - Providing more specific hints in the question

4. **Debug LLM responses**: Add logging to see what the LLM is thinking at each step

### Files Created

- `agent.py` - Main agent implementation with agentic loop
- `.env.agent.secret` - LLM configuration
- `AGENT.md` - Architecture documentation
- `tests/test_agent_tools.py` - Regression tests
- `plans/task-3.md` - This plan file
