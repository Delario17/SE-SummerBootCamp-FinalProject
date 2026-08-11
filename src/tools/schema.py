"""Tool definitions in OpenAI function-calling JSON Schema format."""

READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read the contents of a file at the given path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the file to read.",
                },
            },
            "required": ["path"],
        },
    },
}

WRITE_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write content to a file, creating it if it does not exist.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the file to write.",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file.",
                },
            },
            "required": ["path", "content"],
        },
    },
}

RUN_SHELL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "run_shell",
        "description": "Execute a shell command and return its output.",
        "parameters": {
            "type": "object",
            "properties": {
                "cmd": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory for the command (optional).",
                },
            },
            "required": ["cmd"],
        },
    },
}

FINISH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "finish",
        "description": "Declare the task as finished and provide a summary.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "A summary of what was accomplished.",
                },
            },
            "required": ["summary"],
        },
    },
}

TOOL_SCHEMAS = [READ_FILE_SCHEMA, WRITE_FILE_SCHEMA, RUN_SHELL_SCHEMA, FINISH_SCHEMA]

_SCHEMA_MAP = {t["function"]["name"]: t for t in TOOL_SCHEMAS}


def get_tool_schema(name: str) -> dict:
    """Get the JSON Schema for a specific tool by name.

    Raises:
        ValueError: If the tool name is not recognized.
    """
    if name not in _SCHEMA_MAP:
        raise ValueError(f"Unknown tool: {name}. Available: {list(_SCHEMA_MAP.keys())}")
    return _SCHEMA_MAP[name]


def get_allowed_tools(allowed: list[str]) -> list[dict]:
    """Filter tool schemas to only those in the allowed list."""
    return [s for s in TOOL_SCHEMAS if s["function"]["name"] in allowed]