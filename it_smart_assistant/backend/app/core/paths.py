"""Project path helpers that work on host and inside Docker containers."""

from __future__ import annotations

from pathlib import Path


def resolve_project_root(start: Path) -> Path:
    """Resolve the effective project root for the current runtime.

    Host layout:
    - <project>/backend/app/...

    Container layout:
    - /app/app/...
    - /app/knowledge_raw
    - /app/knowledge_admin
    - /app/knowledge_processed
    """

    current = start.resolve()

    for candidate in [current, *current.parents]:
        if (candidate / "knowledge_raw").exists() or (candidate / "knowledge_admin").exists():
            return candidate
        if (candidate / "app").exists() and (candidate / "cli").exists():
            return candidate

    return current.parents[2]
