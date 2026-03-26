#!/usr/bin/env python3
"""Regression tests for the agent tools.

These tests verify that the agent uses the correct tools for different types of questions.
"""

import json
import subprocess
import sys
from pathlib import Path


def run_agent(question: str) -> dict:
    """Run agent.py with the given question and return the parsed JSON output."""
    result = subprocess.run(
        [sys.executable, "agent.py", question],
        capture_output=True,
        text=True,
        timeout=120,
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Agent failed: {result.stderr}")
    
    return json.loads(result.stdout)


def test_wiki_question_uses_read_file():
    """Test that a wiki question triggers read_file tool usage."""
    question = "According to the project wiki, what steps are needed to protect a branch on GitHub?"
    
    result = run_agent(question)
    
    # Check that tool_calls is populated
    assert "tool_calls" in result, "Missing tool_calls field"
    assert len(result["tool_calls"]) > 0, "No tool calls were made"
    
    # Check that read_file was used (along with list_files)
    tools_used = {tc["tool"] for tc in result["tool_calls"]}
    assert "read_file" in tools_used, f"Expected read_file in tool calls, got: {tools_used}"
    
    # Check that answer is provided
    assert "answer" in result, "Missing answer field"
    assert len(result["answer"]) > 0, "Empty answer"
    
    # Check that source is provided for wiki questions
    assert "source" in result, "Missing source field"
    assert result["source"].startswith("wiki/"), f"Expected wiki source, got: {result['source']}"
    
    print("✓ test_wiki_question_uses_read_file passed")


def test_database_question_uses_query_api():
    """Test that a database question triggers query_api tool usage."""
    question = "How many items are in the database?"
    
    result = run_agent(question)
    
    # Check that tool_calls is populated
    assert "tool_calls" in result, "Missing tool_calls field"
    assert len(result["tool_calls"]) > 0, "No tool calls were made"
    
    # Check that query_api was used
    tools_used = {tc["tool"] for tc in result["tool_calls"]}
    assert "query_api" in tools_used, f"Expected query_api in tool calls, got: {tools_used}"
    
    # Check that answer is provided
    assert "answer" in result, "Missing answer field"
    assert len(result["answer"]) > 0, "Empty answer"
    
    print("✓ test_database_question_uses_query_api passed")


if __name__ == "__main__":
    # Change to project root
    project_root = Path(__file__).parent.parent
    import os
    os.chdir(project_root)
    
    # Run tests
    test_wiki_question_uses_read_file()
    test_database_question_uses_query_api()
    
    print("\nAll tests passed!")
