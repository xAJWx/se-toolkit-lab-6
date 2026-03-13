# Task 2: The Documentation Agent - Implementation Plan

## Overview

Transform the basic LLM caller from Task 1 into a true agent with tool-calling capabilities. The agent will navigate the project wiki to answer questions about workflows and procedures.

## Tool Definitions

### 1. `list_files(path: str)`

- **Purpose**: Discover available documentation files
- **Parameters**:
  - `path`: Relative directory path from project root
- **Returns**: Newline-separated list of files and directories
- **Security**: Validate path to prevent directory traversal attacks
- **Implementation**: Use `os.listdir()` with path validation

### 2. `read_file(path: str)`

- **Purpose**: Read specific documentation files to find answers
- **Parameters**:
  - `path`: Relative file path from project root
- **Returns**: File contents as string or error message
- **Security**: Validate path and check file exists
- **Implementation**: Use `open()` with proper error handling

## Agentic Loop Design

### Loop Structure
