
"""Tests for the Documentation Agent (Task 2)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def agent_script():
    """Return the path to agent.py."""
    return Path(__file__).parent.parent / "agent.py"


def create_test_wiki():
    """Create a test wiki structure for testing."""
    wiki_dir = Path(__file__).parent.parent / "wiki"
    wiki_dir.mkdir(exist_ok=True)
    
    # Create git-workflow.md
    git_workflow = wiki_dir / "git-workflow.md"
    if not git_workflow.exists():
        git_workflow.write_text("""# Git Workflow

## Resolving Merge Conflicts

When you encounter a merge conflict:

1. Open the conflicting files
2. Look for conflict markers: <<<<<<<, =======, >>>>>>>
3. Choose which changes to keep or combine them
4. Remove the conflict markers
5. Stage the resolved files: `git add <file>`
6. Complete the merge: `git commit`

## Creating Branches

Use `git checkout -b <branch-name>` to create and switch to a new branch.
""")
    
    # Create another test file
    pr_workflow = wiki_dir / "pull-requests.md"
    if not pr_workflow.exists():
        pr_workflow.write_text("""# Pull Requests

## Creating a Pull Request

1. Push your branch to GitHub
2. Go to the repository on GitHub
3. Click "Pull Request" button
4. Select your branch
5. Add description and create PR
""")
    
    return wiki_dir


def test_merge_conflict_question(agent_script):
    """Test that agent uses read_file for merge conflict questions."""
    create_test_wiki()
    
    result = subprocess.run(
        [sys.executable, str(agent_script), "How do you resolve a merge conflict?"],
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
    assert "source" in output
    assert "tool_calls" in output
    
    # Check that tool_calls contains read_file
    tool_calls = output["tool_calls"]
    assert len(tool_calls) > 0
    
    # Look for read_file in tool calls
    read_file_calls = [tc for tc in tool_calls if tc["tool"] == "read_file"]
    assert len(read_file_calls) > 0, "Expected at least one read_file tool call"
    
    # Check that it read git-workflow.md
    git_files = [tc for tc in read_file_calls if "git-workflow.md" in tc["args"].get("path", "")]
    assert len(git_files) > 0, "Expected to read git-workflow.md"
    
    # Source should reference git-workflow.md
    assert "git-workflow.md" in output["source"], "Source should reference git-workflow.md"
    
    # Answer should contain relevant information
    assert "merge conflict" in output["answer"].lower() or "conflict markers" in output["answer"].lower()


def test_list_wiki_files(agent_script):
    """Test that agent uses list_files to discover wiki contents."""
    create_test_wiki()
    
    result = subprocess.run(
        [sys.executable, str(agent_script), "What files are in the wiki?"],
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
    assert "source" in output
    assert "tool_calls" in output
    
    # Check that tool_calls contains list_files
    tool_calls = output["tool_calls"]
    assert len(tool_calls) > 0
    
    # Look for list_files in tool calls
    list_files_calls = [tc for tc in tool_calls if tc["tool"] == "list_files"]
    assert len(list_files_calls) > 0, "Expected at least one list_files tool call"
    
    # Check that it listed the wiki directory
    wiki_listings = [tc for tc in list_files_calls if "wiki" in tc["args"].get("path", "")]
    assert len(wiki_listings) > 0, "Expected to list wiki directory"
    
    # Answer should mention the files
    answer = output["answer"].lower()
    assert "git-workflow.md" in answer or "pull-requests.md" in answer


def test_path_traversal_prevention(agent_script):
    """Test that agent prevents directory traversal attacks."""
    create_test_wiki()
    
    # Try to access a file outside project
    result = subprocess.run(
        [sys.executable, str(agent_script), "Can you read /etc/passwd?"],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    assert result.returncode == 0
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("Invalid JSON output")
    
    # Check that any read_file attempts were blocked
    tool_calls = output.get("tool_calls", [])
    read_file_calls = [tc for tc in tool_calls if tc["tool"] == "read_file"]
    
    for tc in read_file_calls:
        if "result" in tc:
            assert "Error:" in tc["result"] or "Access denied" in tc["result"]


def test_nonexistent_file_handling(agent_script):
    """Test that agent handles non-existent files gracefully."""
    create_test_wiki()
    
    result = subprocess.run(
        [sys.executable, str(agent_script), "What does the file nonexistent.md say?"],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    assert result.returncode == 0
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("Invalid JSON output")
    
    # The agent should report that the file doesn't exist
    answer = output["answer"].lower()
    assert "doesn't exist" in answer or "not exist" in answer or "couldn't find" in answer


def test_tool_calls_structure(agent_script):
    """Test that tool_calls have the correct structure."""
    create_test_wiki()
    
    result = subprocess.run(
        [sys.executable, str(agent_script), "What files are in the wiki?"],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    assert result.returncode == 0
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("Invalid JSON output")
    
    tool_calls = output.get("tool_calls", [])
    
    for tc in tool_calls:
        # Each tool call should have tool, args, and result
        assert "tool" in tc
        assert "args" in tc
        assert "result" in tc
        
        # args should be a dict
        assert isinstance(tc["args"], dict)
        
        # result should be a string
        assert isinstance(tc["result"], str)