"""
Documentation Agent - CLI tool with tool-calling capabilities.
Can read files and list directories to answer questions about the project wiki.
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


class ToolDefinition(BaseModel):
    """Definition of a tool for the LLM function calling API."""
    type: str = "function"
    function: Dict[str, Any]


class AgentConfig(BaseModel):
    """Configuration for the LLM agent."""
    api_key: str
    api_base: str
    model: str
    max_tool_calls: int = 10


# ============= Configuration =============

def load_config() -> AgentConfig:
    """Load configuration from environment variables."""
    load_dotenv(".env.agent.secret")
    
    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL")
    
    if not all([api_key, api_base, model]):
        raise ValueError(
            "Missing required environment variables. "
            "Please set LLM_API_KEY, LLM_API_BASE, and LLM_MODEL in .env.agent.secret"
        )
    
    return AgentConfig(
        api_key=api_key,
        api_base=api_base,
        model=model
    )


# ============= Tool Implementations =============

class Tools:
    """Tool implementations with security validation."""
    
    PROJECT_ROOT = Path(__file__).parent.absolute()
    
    @classmethod
    def validate_path(cls, path: str) -> Path:
        """
        Validate and resolve a path to prevent directory traversal.
        Raises ValueError if path is outside project directory.
        """
        # Convert to Path object and resolve
        requested_path = (cls.PROJECT_ROOT / path).resolve()
        
        # Check if the resolved path is within project root
        if not str(requested_path).startswith(str(cls.PROJECT_ROOT)):
            raise ValueError(f"Access denied: Path '{path}' is outside project directory")
        
        return requested_path
    
    @classmethod
    def list_files(cls, path: str = ".") -> str:
        """
        List files and directories at the given path.
        
        Args:
            path: Relative directory path from project root
            
        Returns:
            Newline-separated listing of entries
        """
        try:
            validated_path = cls.validate_path(path)
            
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
    
    @classmethod
    def read_file(cls, path: str) -> str:
        """
        Read a file from the project repository.
        
        Args:
            path: Relative file path from project root
            
        Returns:
            File contents as string
        """
        try:
            validated_path = cls.validate_path(path)
            
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


# ============= Tool Schemas =============

def get_tool_definitions() -> List[Dict[str, Any]]:
    """Return the tool definitions for LLM function calling."""
    
    return [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path. Use this to discover what documentation is available.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path from project root (e.g., 'wiki' or 'wiki/git')",
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
                "description": "Read a file from the project repository. Use this to read documentation files and find answers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative file path from project root (e.g., 'wiki/git-workflow.md')"
                        }
                    },
                    "required": ["path"]
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
    """
    Call the LLM with tool definitions.
    Returns (content, tool_calls).
    """
    
    url = f"{config.api_base}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.api_key}"
    }
    
    payload = {
        "model": config.model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.3,  # Lower temperature for more focused responses
        "max_tokens": 2000
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            message = data["choices"][0]["message"]
            content = message.get("content", "")
            tool_calls = message.get("tool_calls")
            
            return content, tool_calls
            
    except Exception as e:
        print(f"LLM API error: {str(e)}", file=sys.stderr)
        raise


def execute_tool_call(tool_call: Dict[str, Any]) -> str:
    """Execute a tool call and return the result."""
    
    function_name = tool_call["function"]["name"]
    arguments = json.loads(tool_call["function"]["arguments"])
    
    print(f"Executing tool: {function_name} with args: {arguments}", file=sys.stderr)
    
    if function_name == "list_files":
        return Tools.list_files(**arguments)
    elif function_name == "read_file":
        return Tools.read_file(**arguments)
    else:
        return f"Error: Unknown tool '{function_name}'"


async def run_agentic_loop(question: str, config: AgentConfig) -> LLMResponse:
    """
    Run the agentic loop:
    1. Send messages to LLM with tools
    2. If tool_calls → execute → append results → repeat
    3. If no tool_calls → extract answer and return
    """
    
    # System prompt
    system_prompt = """You are a documentation assistant for a software engineering toolkit.
Your goal is to answer questions using the project wiki files.

Available tools:
- list_files(path): Discover what documentation exists at a given path
- read_file(path): Read specific files to find answers

Strategy:
1. First use list_files("wiki") to see what documentation is available
2. Then use read_file on relevant files to find specific information
3. When you find the answer, include the source reference in the format: wiki/filename.md#section-anchor
   (For example: wiki/git-workflow.md#resolving-merge-conflicts)
4. If you can't find the answer, explain what you found and suggest what files might help

Remember to:
- Always check if files exist before reading them
- If a file doesn't exist, try alternative paths
- Include the source in your final answer
- Be concise but informative"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    
    tools = get_tool_definitions()
    tool_calls_history = []
    
    for iteration in range(config.max_tool_calls):
        print(f"\n--- Iteration {iteration + 1} ---", file=sys.stderr)
        
        # Call LLM
        content, tool_calls = await call_llm_with_tools(messages, tools, config)
        
        # If no tool calls, we have the final answer
        if not tool_calls:
            print("No more tool calls, extracting answer...", file=sys.stderr)
            
            # Try to extract source from content (look for wiki/*.md#* pattern)
            import re
            source_match = re.search(r'(wiki/[\w/-]+\.md(?:#[\w-]+)?)', content)
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
            result = execute_tool_call(tc)
            
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
    # Check command line arguments
    if len(sys.argv) != 2:
        print("Usage: uv run agent.py 'Your question here'", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    
    try:
        # Load configuration
        config = load_config()
        
        # Run agentic loop
        result = asyncio.run(run_agentic_loop(question, config))
        
        # Output JSON to stdout
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
        
    except (ValueError, ValidationError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()