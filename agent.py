#!/usr/bin/env python3
"""Agent CLI for the SE Toolkit Lab.

This agent can:
1. Read files from the project wiki (read_file, list_files)
2. Query the backend API (query_api)
3. Answer questions using an LLM with function calling

Usage:
    uv run agent.py "Your question here"

Output:
    JSON with answer, source, and tool_calls fields
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Load environment variables from .env.agent.secret
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.resolve()
env_file = PROJECT_ROOT / ".env.agent.secret"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

# ---------------------------------------------------------------------------
# Configuration from environment variables
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.resolve()

# LLM configuration
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_API_BASE = os.environ.get("LLM_API_BASE", "http://localhost:8080/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3-coder-plus")

# Backend API configuration
LMS_API_KEY = os.environ.get("LMS_API_KEY", "my-secret-api-key")
AGENT_API_BASE_URL = os.environ.get("AGENT_API_BASE_URL", "http://localhost:42002")

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def read_file(path: str) -> str:
    """Read a file from the project repository.

    Args:
        path: Relative path from project root (e.g., "wiki/git-workflow.md")

    Returns:
        File contents as string, or error message if file doesn't exist
    """
    # Security: prevent path traversal
    if ".." in path or path.startswith("/"):
        return f"Error: Invalid path - path traversal not allowed"

    full_path = PROJECT_ROOT / path
    if not str(full_path.resolve()).startswith(str(PROJECT_ROOT)):
        return f"Error: Path must be within project directory"

    if not full_path.exists():
        return f"Error: File not found: {path}"

    try:
        return full_path.read_text()
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(path: str) -> str:
    """List files and directories at a given path.

    Args:
        path: Relative directory path from project root (e.g., "wiki")

    Returns:
        Newline-separated listing of entries, or error message
    """
    # Security: prevent path traversal
    if ".." in path or path.startswith("/"):
        return f"Error: Invalid path - path traversal not allowed"

    full_path = PROJECT_ROOT / path
    if not str(full_path.resolve()).startswith(str(PROJECT_ROOT)):
        return f"Error: Path must be within project directory"

    if not full_path.exists():
        return f"Error: Directory not found: {path}"

    if not full_path.is_dir():
        return f"Error: Not a directory: {path}"

    entries = []
    for entry in sorted(full_path.iterdir()):
        suffix = "/" if entry.is_dir() else ""
        entries.append(f"{entry.name}{suffix}")

    return "\n".join(entries)


def query_api(method: str, path: str, body: str | None = None, use_auth: bool = True) -> str:
    """Query the backend API.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        path: API endpoint path (e.g., "/items/", "/analytics/completion-rate")
        body: Optional JSON request body for POST/PUT requests
        use_auth: Whether to use LMS_API_KEY for authentication (default True)

    Returns:
        JSON string with status_code and body fields
    """
    url = f"{AGENT_API_BASE_URL}{path}"

    headers = {
        "Content-Type": "application/json",
    }
    
    if use_auth:
        headers["Authorization"] = f"Bearer {LMS_API_KEY}"

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            data = json.loads(body) if body else {}
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "PUT":
            data = json.loads(body) if body else {}
            response = requests.put(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            return json.dumps({
                "status_code": 400,
                "body": {"error": f"Unsupported method: {method}"}
            })

        result = {
            "status_code": response.status_code,
            "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        }
        return json.dumps(result)

    except requests.exceptions.Timeout:
        return json.dumps({"status_code": 408, "body": {"error": "Request timed out"}})
    except requests.exceptions.ConnectionError as e:
        return json.dumps({"status_code": 0, "body": {"error": f"Connection error: {e}"}})
    except json.JSONDecodeError as e:
        return json.dumps({"status_code": 200, "body": {"error": f"Invalid JSON response: {e}"}})
    except Exception as e:
        return json.dumps({"status_code": 500, "body": {"error": str(e)}})


# ---------------------------------------------------------------------------
# Tool schemas for LLM function calling
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the project repository. Use this to read source code files or documentation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path. Use this to discover the project structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Query the backend API for data or system information. Use this for questions about items in the database, analytics, scores, completion rates, etc. Do NOT use for reading source code files. For questions about authentication errors, set use_auth=false.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method (GET, POST, PUT, DELETE)"
                    },
                    "path": {
                        "type": "string",
                        "description": "API endpoint path (e.g., '/items/', '/analytics/completion-rate')"
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional JSON request body for POST/PUT requests"
                    },
                    "use_auth": {
                        "type": "boolean",
                        "description": "Whether to use LMS_API_KEY for authentication. Set to false for testing unauthenticated access (default: true)"
                    }
                },
                "required": ["method", "path"]
            }
        }
    }
]

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a helpful assistant for a software engineering lab.

## Tools

1. **read_file** - Read a file (path relative to project root, e.g., "backend/app/main.py")
2. **list_files** - List directory contents (path relative to project root, e.g., "wiki", "backend/app/routers")
3. **query_api** - Query backend API (method, path, optional body)

## Rules

1. **Use minimum tool calls** - aim for 1-3 tool calls maximum
2. **Stop immediately after finding the answer** - do not continue exploring
3. **For simple questions** (facts, numbers) - use query_api directly
4. **For wiki questions** - use list_files("wiki"), then read_file for the relevant file
5. **For source code questions** - read the most likely file directly (e.g., "backend/app/main.py")
6. **For "list all" questions** - use list_files on the specific directory, then read each file

## Answer Format

- Give a **concise, direct answer** in 1-5 sentences
- Include **source** field with the file path where you found the answer
- Do not explain your reasoning, just give the answer

## Examples

Q: "How many items are in the database?"
→ Use: query_api(GET, "/items/")
→ Answer: "There are X items."

Q: "What steps to protect a branch?"
→ Use: read_file("wiki/github.md")
→ Answer: "Steps: 1)... 2)..." Source: "wiki/github.md"

Q: "What framework does the backend use?"
→ Use: read_file("backend/app/main.py")
→ Answer: "FastAPI" Source: "backend/app/main.py"

Q: "List all API routers"
→ Use: list_files("backend/app/routers"), then read each .py file
→ Answer: "items.py - items, learners.py - learners, ..." Source: "backend/app/routers/"
"""

# ---------------------------------------------------------------------------
# LLM interaction
# ---------------------------------------------------------------------------


def call_llm(messages: list[dict[str, Any]], max_tokens: int = 2000) -> dict[str, Any]:
    """Call the LLM API with function calling support.

    Args:
        messages: List of message dicts with role and content
        max_tokens: Maximum tokens in response

    Returns:
        Response message dict from LLM
    """
    url = f"{LLM_API_BASE}/chat/completions"

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]


# ---------------------------------------------------------------------------
# Agentic loop
# ---------------------------------------------------------------------------

TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
    "query_api": query_api,
}


def run_agent(question: str, max_iterations: int = 12) -> dict[str, Any]:
    """Run the agentic loop to answer a question.

    Args:
        question: User's question
        max_iterations: Maximum number of tool call iterations (default 5 for faster responses)

    Returns:
        Dict with answer, source, and tool_calls
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    tool_calls_log = []
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        # Call LLM
        response = call_llm(messages)

        # Check for tool calls
        tool_calls = response.get("tool_calls") or []

        if not tool_calls:
            # No tool calls - final answer
            answer = (response.get("content") or "").strip()
            return {
                "answer": answer,
                "source": extract_source(answer, messages),
                "tool_calls": tool_calls_log,
            }

        # Add the assistant's tool call request to messages FIRST
        messages.append(response)

        # Execute tool calls
        for tool_call in tool_calls:
            func_name = tool_call["function"]["name"]
            func_args = json.loads(tool_call["function"]["arguments"])

            # Execute the tool
            if func_name in TOOL_FUNCTIONS:
                result = TOOL_FUNCTIONS[func_name](**func_args)
            else:
                result = f"Error: Unknown tool '{func_name}'"

            # Log the tool call
            tool_calls_log.append({
                "tool": func_name,
                "args": func_args,
                "result": result,
            })

            # Add tool result to messages (AFTER assistant message)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result,
            })

    # Max iterations reached - ask LLM to provide final answer based on gathered information
    messages.append({
        "role": "user",
        "content": "You have reached the maximum number of tool calls. Please provide your final answer based on the information you have gathered."
    })
    
    try:
        final_response = call_llm(messages)
        answer = (final_response.get("content") or "").strip()
    except:
        answer = "I was unable to complete this question within the iteration limit."
    
    return {
        "answer": answer,
        "source": extract_source(answer, messages),
        "tool_calls": tool_calls_log,
    }


def extract_source(answer: str, messages: list[dict]) -> str:
    """Extract source reference from the conversation.

    Looks for file paths mentioned in tool calls or the answer.
    """
    # First, check for read_file tool calls - these are the most likely sources
    # Return the FIRST read_file call, as it's usually the primary source
    for tool_call in messages:
        if tool_call.get("role") == "assistant" and tool_call.get("tool_calls"):
            for tc in tool_call["tool_calls"]:
                if tc["function"]["name"] == "read_file":
                    args = json.loads(tc["function"]["arguments"])
                    path = args.get("path", "")
                    if path.endswith(".py") or path.endswith(".md") or path.endswith(".toml"):
                        return path
    
    # Check tool results for wiki file references
    for msg in messages:
        if msg.get("role") == "tool":
            content = msg.get("content") or ""
            # Look for wiki file references
            if "wiki/" in content:
                for line in content.split("\n"):
                    if "wiki/" in line and line.endswith(".md"):
                        return line.strip().split()[0]
    
    # Check if answer itself contains a file reference
    if "backend/" in answer or "wiki/" in answer:
        import re
        # Look for common file patterns
        match = re.search(r'(backend/[\w/.]+\.py|wiki/[\w-]+\.md|pyproject\.toml)', answer)
        if match:
            return match.group(1)

    return ""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
        sys.exit(1)

    question = " ".join(sys.argv[1:])

    try:
        result = run_agent(question)
    except Exception as e:
        # Always return valid JSON, even on error
        import traceback
        tb = traceback.format_exc()
        print(f"[ERROR] {tb}", file=sys.stderr)
        result = {
            "answer": f"Error: {str(e)}",
            "source": "",
            "tool_calls": []
        }

    # Output JSON
    try:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        # Fallback if JSON serialization fails
        print(f'{{"answer": "Error serializing response: {str(e)}", "source": "", "tool_calls": []}}')


if __name__ == "__main__":
    main()
