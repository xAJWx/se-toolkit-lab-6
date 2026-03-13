# Task 3: The System Agent - Implementation Plan

## Overview

Add a `query_api` tool to the documentation agent from Task 2, enabling it to interact with the deployed backend. The agent will now answer:

- Static system facts (framework, ports, status codes) - via `read_file`
- Data-dependent queries (item count, scores) - via `query_api`
- Wiki documentation questions - via `list_files` and `read_file`

## Tool Definition: query_api

### Parameters

- `method` (string): HTTP method (GET, POST, etc.)
- `path` (string): API endpoint path (e.g., "/items/")
- `body` (string, optional): JSON request body for POST requests

### Returns

JSON string with:

```json
{
  "status_code": 200,
  "body": {...}  # Parsed response body
}
