"""Register pilot projects from fixture paths or environment variables."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from fade_infrastructure.settings import get_settings
from tests.fixtures.pilot_repo import materialize_named_pilot_repo


async def register_pilot(name: str, source_path: Path, *, tags: list[str]) -> str:
    import httpx

    base = os.environ.get("FADE_API_BASE_URL", "http://127.0.0.1:8000")
    async with httpx.AsyncClient(base_url=base, timeout=30.0) as client:
        response = await client.post(
            "/api/v1/projects",
            json={
                "name": name,
                "source_path": str(source_path),
                "tags": tags,
            },
        )
        response.raise_for_status()
        return response.json()["id"]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Register FADE pilot projects")
    parser.add_argument(
        "--fixture",
        choices=["pilot-small", "neurostring", "tradepilot"],
        default="pilot-small",
    )
    parser.add_argument("--path", help="Existing git repo path (skip fixture materialization)")
    parser.add_argument("--name", help="Project display name")
    parser.add_argument("--api", default=os.environ.get("FADE_API_BASE_URL", "http://127.0.0.1:8000"))
    args = parser.parse_args()

    settings = get_settings()
    target_root = settings.var_dir / "pilots"
    target_root.mkdir(parents=True, exist_ok=True)

    if args.path:
        repo_path = Path(args.path).resolve()
    else:
        repo_path = materialize_named_pilot_repo(target_root / args.fixture, args.fixture)

    name = args.name or {
        "pilot-small": "Pilot Small",
        "neurostring": "NeuroString Pilot",
        "tradepilot": "TradePilot Paper",
    }[args.fixture]

    os.environ["FADE_API_BASE_URL"] = args.api
    if not settings.allowed_project_roots:
        os.environ["FADE_PROJECT_ALLOWED_ROOTS"] = str(repo_path.parent)
        get_settings.cache_clear()

    project_id = await register_pilot(name, repo_path, tags=["pilot", args.fixture])
    print(f"Registered {name}: {project_id}")
    print(f"Source: {repo_path}")


if __name__ == "__main__":
    asyncio.run(main())
