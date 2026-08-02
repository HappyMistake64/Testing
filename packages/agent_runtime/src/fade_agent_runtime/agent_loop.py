"""Tool-assisted context gathering for implementation jobs."""

from __future__ import annotations

from pathlib import Path

from fade_domain.goal import Goal
from fade_tool_gateway.gateway import ToolGateway, ToolGatewayError

from fade_agent_runtime.implementation import collect_context_files, default_context_paths


def gather_context_via_tools(
    workspace_path: Path,
    goal: Goal,
    *,
    max_files: int = 5,
) -> dict[str, str]:
    """Use read-only tool gateway to discover and load workspace context."""
    gateway = ToolGateway.for_workspace(workspace_path)
    paths = list(default_context_paths(workspace_path))

    for listing_root in ("src", "."):
        try:
            listing = gateway.list_dir(listing_root)
        except ToolGatewayError:
            continue
        for entry in listing.entries:
            if entry.is_dir:
                try:
                    nested = gateway.list_dir(entry.path)
                except ToolGatewayError:
                    continue
                for nested_entry in nested.entries:
                    if nested_entry.is_dir:
                        continue
                    if nested_entry.path.endswith((".py", ".ts", ".tsx", ".js")):
                        paths.append(nested_entry.path)
                continue
            if entry.path.endswith((".py", ".ts", ".tsx", ".js")):
                paths.append(entry.path)
            if len(paths) >= max_files * 2:
                break

    intent_lower = goal.intent.lower()
    for entry_path in list(paths):
        name = Path(entry_path).name.lower()
        if name in intent_lower or Path(entry_path).stem.lower() in intent_lower:
            paths.insert(0, entry_path)

    unique_paths: list[str] = []
    for path in paths:
        if path not in unique_paths:
            unique_paths.append(path)
        if len(unique_paths) >= max_files:
            break

    context = collect_context_files(workspace_path, relative_paths=unique_paths)
    if not context and unique_paths:
        context = collect_context_files(workspace_path, relative_paths=unique_paths[:1])
    return context
