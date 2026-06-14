"""Built-in tools: sandboxed file operations.

All paths are resolved relative to a single workspace directory and validated to
stay inside it, so the agent cannot read or write outside its sandbox.
"""
from __future__ import annotations

from pathlib import Path

from .registry import Tool, ToolRegistry


def _resolve(workspace: Path, raw_path: str) -> Path:
    """Resolve `raw_path` under `workspace`, rejecting any escape attempt."""
    workspace = workspace.resolve()
    candidate = (workspace / raw_path).resolve()
    if candidate != workspace and workspace not in candidate.parents:
        raise ValueError(f"path {raw_path!r} escapes the workspace sandbox")
    return candidate


def make_default_registry(workspace: Path) -> ToolRegistry:
    """A registry with read_file / write_file / list_dir scoped to `workspace`."""
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    registry = ToolRegistry()

    def read_file(args: dict) -> str:
        path = _resolve(workspace, args["path"])
        if not path.is_file():
            return f"Error: no such file: {args['path']}"
        return path.read_text(encoding="utf-8")

    def write_file(args: dict) -> str:
        path = _resolve(workspace, args["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args["content"], encoding="utf-8")
        return f"Wrote {len(args['content'])} chars to {args['path']}"

    def list_dir(args: dict) -> str:
        path = _resolve(workspace, args.get("path", "."))
        if not path.is_dir():
            return f"Error: not a directory: {args.get('path', '.')}"
        entries = sorted(p.name + ("/" if p.is_dir() else "") for p in path.iterdir())
        return "\n".join(entries) if entries else "(empty)"

    registry.register(
        Tool(
            name="read_file",
            description="Read a UTF-8 text file from the workspace.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace root."}
                },
                "required": ["path"],
            },
            handler=read_file,
        )
    )
    registry.register(
        Tool(
            name="write_file",
            description="Create or overwrite a UTF-8 text file in the workspace.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace root."},
                    "content": {"type": "string", "description": "Full file contents to write."},
                },
                "required": ["path", "content"],
            },
            handler=write_file,
        )
    )
    registry.register(
        Tool(
            name="list_dir",
            description="List the entries of a directory in the workspace.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory relative to the workspace root. Defaults to root."}
                },
                "required": [],
            },
            handler=list_dir,
        )
    )
    return registry
