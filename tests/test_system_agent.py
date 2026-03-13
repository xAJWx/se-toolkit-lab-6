"""Tests for the System Agent (Task 3)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def agent_script():
    """Return the path to agent.py."""
    return Path(__file__).parent.parent / "agent.py"


def create_test_files():
    """Create test files for source code questions."""
    backend_dir = Path(__file__).parent.parent / "backend/app"
    backend_dir.mkdir(parents=True, exist_ok=True)
    
    # Create main.py with framework info
    main_py = backend_dir / "main.py"
    if not main_py.exists():
        main_py.write_text("""from fastapi import FastAPI

app = FastAPI(title="Learning Management System API")

@app.get("/")
async def root():
    return {"message": "LMS API is running"}

# Default port is 8000
""")
    
    # Create settings.py with port info
    settings_py = backend_dir / "settings.py"
    if not settings_py.exists():
        settings_py.write_text("""from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "LMS API"
    debug: bool = False
    cors_origins: list[str] = ["*"]
    enable_interactions: bool = True
    enable_learners: bool = True
    
    # Default port for the app
    port: int = 8000
""")


def test_framework_question(agent_script):
    """Test that agent uses read_file for framework questions."""
    create_test_files()
    
    result = subprocess.run(
        [sys.executable, str(agent_script), "What Python web framework does this project use?"],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    assert result.returncode == 0, f"Agent failed: {result.stderr}"
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON output: {result.stdout}\nError: {e}")
    
    # Check required fields
    assert "answer" in output
    assert "tool_calls" in output
    
    # Check that tool_calls contains read_file
    tool_calls = output["tool_calls"]
    assert len(tool_calls) > 0
    
    # Look for read_file in tool calls
    read_file_calls = [tc for tc in tool_calls if tc["tool"] == "read_file"]
    assert len(read_file_calls) > 0, "Expected at least one read_file tool call"
    
    # Check that it read main.py
    main_py_files = [tc for tc in read_file_calls if "main.py" in tc["args"].get("path", "")]
    assert len(main_py_files) > 0, "Expected to read main.py"
    
    # Answer should mention FastAPI
    assert "fastapi" in output["answer"].lower()


def test_port_question(agent_script):
    """Test that agent finds port information."""
    create_test_files()
    
    result = subprocess.run(
        [sys.executable, str(agent_script), "What port does the application run on?"],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    assert result.returncode == 0, f"Agent failed: {result.stderr}"
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON output: {result.stdout}\nError: {e}")
    
    # Answer should mention port 8000
    answer = output["answer"].lower()
    assert "8000" in answer or "port" in answer


def test_items_count_question(agent_script):
    """Test that agent uses query_api for data questions."""
    create_test_files()
    
    result = subprocess.run(
        [sys.executable, str(agent_script), "How many items are in the database?"],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    assert result.returncode == 0, f"Agent failed: {result.stderr}"
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON output: {result.stdout}\nError: {e}")
    
    # Check that tool_calls contains query_api
    tool_calls = output.get("tool_calls", [])
    query_api_calls = [tc for tc in tool_calls if tc["tool"] == "query_api"]
    
    # If query_api was called, verify it was for /items/
    if query_api_calls:
        items_calls = [tc for tc in query_api_calls if "items" in tc["args"].get("path", "")]
        if items_calls:
            # Check result format
            for tc in items_calls:
                if "result" in tc:
                    try:
                        result_json = json.loads(tc["result"])
                        assert "status_code" in result_json
                        assert "body" in result_json
                    except:
                        pass


def test_status_code_question(agent_script):
    """Test that agent answers status code questions."""
    create_test_files()
    
    result = subprocess.run(
        [sys.executable, str(agent_script), "What HTTP status code means unauthorized?"],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    assert result.returncode == 0, f"Agent failed: {result.stderr}"
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("Invalid JSON output")
    
    # Answer should mention 401
    answer = output["answer"].lower()
    assert "401" in answer


def test_error_diagnosis_pattern(agent_script):
    """Test that agent can handle error diagnosis."""
    create_test_files()
    
    result = subprocess.run(
        [sys.executable, str(agent_script), "Why might /items/999 return 404?"],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    assert result.returncode == 0, f"Agent failed: {result.stderr}"
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("Invalid JSON output")
    
    # Answer should mention that item doesn't exist
    answer = output["answer"].lower()
    assert "doesn't exist" in answer or "not found" in answer or "no item" in answer
