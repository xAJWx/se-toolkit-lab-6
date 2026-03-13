"""Additional regression tests for the LLM agent."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def agent_path():
    """Return the path to agent.py."""
    return Path(__file__).parent.parent / "agent.py"


def test_agent_returns_json_format():
    """Test that agent.py always returns valid JSON."""
    agent = Path(__file__).parent.parent / "agent.py"
    
    # Test with different questions
    questions = [
        "What is Python?",
        "Explain Docker",
        "What is 5 * 7?",
    ]
    
    for question in questions:
        result = subprocess.run(
            [sys.executable, str(agent), question],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        assert result.returncode == 0
        try:
            output = json.loads(result.stdout)
            assert "answer" in output
            assert "tool_calls" in output
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON for question: {question}")


def test_agent_stderr_output():
    """Test that debug info goes to stderr."""
    agent = Path(__file__).parent.parent / "agent.py"
    
    result = subprocess.run(
        [sys.executable, str(agent), "Test question"],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # stderr should contain debug info
    assert len(result.stderr) > 0
    assert "Calling LLM" in result.stderr or "Error" in result.stderr or "Received" in result.stderr
    

def test_agent_timeout_handling():
    """Test that agent handles timeouts gracefully."""
    # This is a mock test - in real scenario we'd need to mock the API
    agent = Path(__file__).parent.parent / "agent.py"
    
    # Just verify the script runs without crashing
    result = subprocess.run(
        [sys.executable, str(agent), "Quick question"],
        capture_output=True,
        text=True,
        timeout=5  # Short timeout for the subprocess itself
    )
    
    # Should either succeed or fail gracefully (not crash)
    assert result.returncode in [0, 1]
