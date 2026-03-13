#!/usr/bin/env python3
"""
System Agent - CLI tool with tool-calling capabilities.
Can read files, list directories, and query the backend API.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError


# ============= Pydantic Models =============

class ToolCall(BaseModel):
    """A tool call made by the LLM."""
    tool: str
    args: Dict[str, Any]
    result: Optional[str] = None


class LLMResponse(BaseModel):
    """Expected response structure from the agent."""
    answer: str
    source: str = ""
    tool_calls: List[ToolCall] = []


class AgentConfig(BaseModel):
    """Configuration for the LLM agent."""
    # LLM config
    llm_api_key: str
    llm_api_base: str
    llm_model: str
    
    # Backend config
    lms_api_key: str
    api_base_url: str
    
    # Agent config
    max_tool_calls: int = 10


# ============= Configuration =============

def load_config() -> AgentConfig:
    """Load configuration from environment variables."""
    # Load both env files
    load_dotenv(".env.agent.secret")
    load_dotenv(".env.docker.secret")
    
    # LLM config
    llm_api_key = os.getenv("LLM_API_KEY")
    llm_api_base = os.getenv("LLM_API_BASE")
    llm_model = os.getenv("LLM_MODEL")
    
    # Backend config
    lms_api_key = os.getenv("LMS_API_KEY")
    api_base_url = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
    
    if not all([llm_api_key, llm_api_base, llm_model]):
        raise ValueError(
            "Missing required LLM environment variables. "
            "Please set LLM_API_KEY, LLM_API_BASE, and LLM_MODEL in .env.agent.secret"
        )
    
    if not lms_api_key:
        raise ValueError(
            "Missing required LMS_API_KEY. "
            "Please set LMS_API_KEY in .env.docker.secret"
        )
    
    return AgentConfig(
        llm_api_key=llm_api_key,
        llm_api_base=llm_api_base,
        llm_model=llm_model,
        lms_api_key=lms_api_key,
        api_base_url=api_base_url
    )


# ============= Tool Implementations =============

class Tools:
    """Tool implementations with security validation."""
    
    PROJECT_ROOT = Path(__file__).parent.absolute()
    
    def __init__(self, config: AgentConfig):
        self.config = config
    
    def validate_path(self, path: str) -> Path:
        """Validate and resolve a path to prevent directory traversal."""
        requested_path = (self.PROJECT_ROOT / path).resolve()
        
        if not str(requested_path).startswith(str(self.PROJECT_ROOT)):
            raise ValueError(f"Access denied: Path '{path}' is outside project directory")
        
        return requested_path
    
    def list_files(self, path: str = ".") -> str:
        """List files and directories at the given path."""
        try:
            validated_path = self.validate_path(path)
            
            if not validated_path.exists():
                return f"Error: Path '{path}' does not exist"
            
            if not validated_path.is_dir():
                return f"Error: Path '{path}' is not a directory"
            
            entries = []
            for entry in validated_path.iterdir():
                suffix = "/" if entry.is_dir() else ""
                entries.append(f"{entry.name}{suffix}")
            
            return "\n".join(sorted(entries))
            
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error listing directory: {str(e)}"
    
    def read_file(self, path: str) -> str:
        """Read a file from the project repository."""
        try:
            validated_path = self.validate_path(path)
            
            if not validated_path.exists():
                return f"Error: File '{path}' does not exist"
            
            if not validated_path.is_file():
                return f"Error: Path '{path}' is not a file"
            
            # Check file size (limit to 1MB)
            if validated_path.stat().st_size > 1024 * 1024:
                return f"Error: File '{path}' is too large (>1MB)"
            
            with open(validated_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        except ValueError as e:
            return f"Error: {str(e)}"
        except UnicodeDecodeError:
            return f"Error: File '{path}' is not a text file"
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    async def query_api(self, method: str, path: str, body: str = "") -> str:
        """Query the backend API."""
        try:
            # Clean up path
            if not path.startswith("/"):
                path = f"/{path}"
            
            url = f"{self.config.api_base_url}{path}"
            
            headers = {
                "X-API-Key": self.config.lms_api_key,
                "Content-Type": "application/json"
            }
            
            print(f"Querying API: {method} {url}", file=sys.stderr)
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, json=json.loads(body) if body else {})
                else:
                    return json.dumps({
                        "status_code": 400,
                        "body": {"error": f"Unsupported method: {method}"}
                    })
                
                # Try to parse response body
                try:
                    body_json = response.json()
                except:
                    body_json = {"text": response.text}
                
                return json.dumps({
                    "status_code": response.status_code,
                    "body": body_json
                })
                
        except httpx.ConnectError:
            return json.dumps({
                "status_code": 503,
                "body": {"error": f"Could not connect to backend at {self.config.api_base_url}"}
            })
        except Exception as e:
            return json.dumps({
                "status_code": 500,
                "body": {"error": str(e)}
            })


# ============= Tool Schemas =============

def get_tool_definitions() -> List[Dict[str, Any]]:
    """Return the tool definitions for LLM function calling."""
    
    return [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path. Use this to discover what documentation or source code is available.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path from project root (e.g., 'wiki' or 'backend/app')",
                            "default": "."
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from the project repository. Use this to read documentation files or source code to find answers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative file path from project root (e.g., 'wiki/git-workflow.md' or 'backend/app/main.py')"
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
                "description": "Query the backend API to get real data from the system. Use this for questions about counts, statistics, or current system state.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "enum": ["GET", "POST"],
                            "description": "HTTP method to use"
                        },
                        "path": {
                            "type": "string",
                            "description": "API endpoint path (e.g., '/items/' or '/analytics/scores?lab=lab-04')"
                        },
                        "body": {
                            "type": "string",
                            "description": "JSON request body for POST requests (optional)",
                            "default": ""
                        }
                    },
                    "required": ["method", "path"]
                }
            }
        }
    ]


# ============= Agent Loop =============

async def call_llm_with_tools(
    messages: List[Dict[str, str]],
    tools: List[Dict[str, Any]],
    config: AgentConfig
) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
    """Call the LLM with tool definitions."""
    
    url = f"{config.llm_api_base}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.llm_api_key}"
    }
    
    payload = {
        "model": config.llm_model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.3,
        "max_tokens": 2000
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            message = data["choices"][0]["message"]
            content = message.get("content") or ""  # Handle null content
            tool_calls = message.get("tool_calls")
            
            return content, tool_calls
            
    except Exception as e:
        print(f"LLM API error: {str(e)}", file=sys.stderr)
        raise


async def execute_tool_call(tool_call: Dict[str, Any], tools_instance: Tools) -> str:
    """Execute a tool call and return the result."""
    
    function_name = tool_call["function"]["name"]
    arguments = json.loads(tool_call["function"]["arguments"])
    
    print(f"Executing tool: {function_name} with args: {arguments}", file=sys.stderr)
    
    if function_name == "list_files":
        return tools_instance.list_files(**arguments)
    elif function_name == "read_file":
        return tools_instance.read_file(**arguments)
    elif function_name == "query_api":
        return await tools_instance.query_api(**arguments)
    else:
        return f"Error: Unknown tool '{function_name}'"


async def run_agentic_loop(question: str, config: AgentConfig) -> LLMResponse:
    """Run the agentic loop with tool calling."""
    
    # System prompt
    system_prompt = """You are a system agent for a software engineering toolkit.
Your goal is to answer questions using three types of tools:

1. **Wiki Documentation** (`list_files`, `read_file` on wiki/) - Use for:
   - How-to questions ("How do I resolve a merge conflict?")
   - Procedures and workflows
   - Best practices

2. **Source Code** (`list_files`, `read_file` on backend/app/) - Use for:
   - Static system facts ("What framework does the backend use?")
   - Configuration ("What port does the app run on?")
   - Error codes and status codes

3. **Backend API** (`query_api`) - Use for:
   - Data queries ("How many items are in the database?")
   - Statistics ("What's the average score?")
   - Current system state

Strategy:
1. First determine what kind of question it is
2. For wiki questions: list_files("wiki") then read_file on relevant files
3. For code questions: explore backend/app/ then read_file on relevant files
4. For data questions: use query_api with appropriate endpoints
5. If you get an error from query_api, try reading the source code to diagnose
6. Include source references when possible (wiki/file.md#section or backend/app/file.py#line)

Remember to:
- Check if files exist before reading them
- Handle API errors gracefully
- Be concise but informative
- Include the source of your information"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    
    tools = get_tool_definitions()
    tools_instance = Tools(config)
    tool_calls_history = []
    
    for iteration in range(config.max_tool_calls):
        print(f"\n--- Iteration {iteration + 1} ---", file=sys.stderr)
        
        # Call LLM
        content, tool_calls = await call_llm_with_tools(messages, tools, config)
        
        # If no tool calls, we have the final answer
        if not tool_calls:
            print("No more tool calls, extracting answer...", file=sys.stderr)
            
            # Try to extract source from content
            import re
            source_match = re.search(r'(wiki/[\w/-]+\.md(?:#[\w-]+)?|backend/[\w/-]+\.py(?:#L\d+)?)', content)
            source = source_match.group(1) if source_match else ""
            
            return LLMResponse(
                answer=content.strip(),
                source=source,
                tool_calls=tool_calls_history
            )
        
        # Execute tool calls
        print(f"Tool calls received: {len(tool_calls)}", file=sys.stderr)
        
        for tc in tool_calls:
            # Execute tool
            result = await execute_tool_call(tc, tools_instance)
            
            # Record in history
            tool_calls_history.append(ToolCall(
                tool=tc["function"]["name"],
                args=json.loads(tc["function"]["arguments"]),
                result=result
            ))
            
            # Add to messages for next iteration
            messages.append({
                "role": "assistant",
                "tool_calls": [tc]
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "name": tc["function"]["name"],
                "content": result
            })
    
    # Max iterations reached
    print(f"Warning: Reached max iterations ({config.max_tool_calls})", file=sys.stderr)
    return LLMResponse(
        answer="I couldn't find a complete answer within the tool call limit.",
        source="",
        tool_calls=tool_calls_history
    )


# ============= Main Entry Point =============

def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: uv run agent.py 'Your question here'", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    
    try:
        config = load_config()
        result = asyncio.run(run_agentic_loop(question, config))
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
        
    except (ValueError, ValidationError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()