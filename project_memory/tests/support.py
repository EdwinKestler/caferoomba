"""Temporary-project helpers shared by Project Memory tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


PROJECT_ID = "65f0db6e-2755-49eb-b6af-68716674ead0"


def write_project(root: Path, documents: dict[str, str] | None = None) -> None:
    documents = documents or {
        "docs/alpha.md": "# Alpha\n\nThe cobalt orchard recovery rule is deterministic.\n",
        "docs/beta.md": "# Beta\n\nThe amber watcher preserves durable cursors.\n",
    }
    for relative, text in documents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    evaluation = root / "project_memory/evaluation/v25.json"
    evaluation.parent.mkdir(parents=True, exist_ok=True)
    cases = [
        {
            "id": f"controlled-{index:02d}",
            "mode": "search",
            "query": "cobalt orchard recovery",
            "expected_paths": ["docs/alpha.md"],
            "forbidden_paths": ["docs/beta.md"],
            "limit": 5,
            "critical": index == 0,
        }
        for index in range(20)
    ]
    evaluation_document = {
        "schema": "project-memory:evaluation:v1",
        "frozen": True,
        "description": "Controlled frozen evaluation fixture excluded from its source corpus.",
        "cases": cases,
    }
    evaluation_raw = (
        json.dumps(evaluation_document, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    evaluation.write_bytes(evaluation_raw)
    config = {
        "project_slug": "memory-fixture",
        "project_id": PROJECT_ID,
        "redis_url_envs": ["PROJECT_MEMORY_URL"],
        "include_patterns": [".project-memory.json", "docs/**/*.md"],
        "exclude_directories": ["project_memory"],
        "exclude_paths": ["project_memory/evaluation/v25.json"],
        "include_project_memory": False,
        "content_scan_allowlist_sha256": [],
        "evaluation_fixture": "project_memory/evaluation/v25.json",
        "evaluation_fixture_sha256": hashlib.sha256(evaluation_raw).hexdigest(),
        "redis_socket_path": ".private/redis.sock",
        "durable_ledger_path": ".private/memory.sqlite3",
        "semantic_provider": {"mode": "disabled"},
    }
    (root / ".project-memory.json").write_text(
        json.dumps(config, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
