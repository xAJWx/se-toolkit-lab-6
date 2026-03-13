#!/usr/bin/env python3
"""
LLM Agent CLI - Calls an LLM and returns structured JSON answers.
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError


class LLMResponse(BaseModel):
    """Expected response structure from the LLM."""
    answer: str
    tool_calls: List[Dict[str, Any]] = []


class AgentConfig(BaseModel):
    """Configuration for the LLM agent."""
    api_key: str
    api_base: str
    model: str


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
    
    return AgentConfig(api_key=api_key, api_base=api_base, model=model)


async def call_llm(question: str, config: AgentConfig) -> LLMResponse:
    """Call the LLM API and return structured response."""
    
    # System prompt (minimal for now)
    system_prompt = "You are a helpful assistant. Provide concise, accurate answers."
    
    # Prepare the request
    url = f"{config.api_base}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.api_key}"
    }
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    # Print debug info to stderr
    print(f"Calling LLM with question: {question}", file=sys.stderr)
    print(f"Using model: {config.model}", file=sys.stderr)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Extract the answer
            answer = data["choices"][0]["message"]["content"].strip()
            
            print(f"Received response (length: {len(answer)} chars)", file=sys.stderr)
            
            return LLMResponse(answer=answer, tool_calls=[])
            
    except httpx.TimeoutException:
        print("Error: Request timed out", file=sys.stderr)
        raise
    except httpx.HTTPStatusError as e:
        print(f"Error: HTTP {e.response.status_code}", file=sys.stderr)
        print(f"Response: {e.response.text}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        raise


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
        
        # Call LLM
        result = asyncio.run(call_llm(question, config))
        
        # Output JSON to stdout
        print(json.dumps(result.dict(), ensure_ascii=False))
        
    except (ValueError, ValidationError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()