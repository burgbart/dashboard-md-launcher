from __future__ import annotations

import re
from pathlib import Path

PROJECT_CONFIG_PATHS = (
    "dashboard-hub/config.yml",
    "dashboard-hub.config.yml",
    ".dashboard-hub/config.yml",
)


def project_config_path(project_path: Path) -> Path | None:
    for relative in PROJECT_CONFIG_PATHS:
        candidate = project_path / relative
        if candidate.exists():
            return candidate
    return None


def read_project_label(project_path: Path) -> str | None:
    config_path = project_config_path(project_path)
    if config_path is None:
        return None
    match = re.search(r'^label:\s*"?([^"\n]+)"?\s*$', config_path.read_text(encoding="utf-8"), re.M)
    if match:
        return match.group(1).strip()
    return None
