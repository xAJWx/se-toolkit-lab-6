"""Regression tests for the LLM agent."""
import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def agent_script():
    """Return the path to agent.py."""
    return Path(__file__).parent.parent / "agent.py"


def test_agent_returns_valid_json(agent_script):
    """Test that agent.py returns valid JSON with required fields."""
    # Run the agent with a simple question
    result = subprocess.run(
        [sys.executable, str(agent_script), "What is 2+2?"],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Check exit code
    assert result.returncode == 0, f"Agent failed with error: {result.stderr}"
    
    # Parse stdout as JSON
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"Output is not valid JSON: {result.stdout}\nError: {e}")
    
    # Check required fields
    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    
    # Check field types
    assert isinstance(output["answer"], str), "'answer' should be a string"
    assert isinstance(output["tool_calls"], list), "'tool_calls' should be a list"
    
    # For task 1, tool_calls should be empty
    assert len(output["tool_calls"]) == 0, "tool_calls should be empty for task 1"
    
    # Answer should be non-empty
    assert output["answer"].strip(), "Answer should not be empty"


def test_agent_handles_missing_argument(agent_script):
    """Test that agent.py handles missing argument gracefully."""
    result = subprocess.run(
        [sys.executable, str(agent_script)],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Should exit with error
    assert result.returncode != 0
    
    # Should print usage to stderr
    assert "Usage:" in result.stderr


def test_agent_handles_long_question(agent_script):
    """Test that agent.py handles long questions."""
    long_question = "What is the meaning of life? " * 10
    result = subprocess.run(
        [sys.executable, str(agent_script), long_question],
        capture_output=True,
        text=True,
        timeout=60  # Longer timeout for long question
    )
    
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert "answer" in output
    assert output["answer"].strip()
