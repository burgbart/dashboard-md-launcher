from __future__ import annotations

import re
from pathlib import Path

PROJECT_CONFIG_PATHS = (
    "dashboard-hub/config.yml",
    "dashboard-hub.config.yml",
    ".dashboard-hub/config.yml",
)

# Built-in label colors used when a project does not override its own color.
LABEL_COLORS = {
    "Backbase": "#58a6ff",
    "Personal": "#a371f7",
}


def project_config_path(project_path: Path) -> Path | None:
    for relative in PROJECT_CONFIG_PATHS:
        candidate = project_path / relative
        if candidate.exists():
            return candidate
    return None


def _read_config_value(project_path: Path, key: str) -> str | None:
    """Read a simple string value from the project's dashboard-hub config.yml."""
    config_path = project_config_path(project_path)
    if config_path is None:
        return None
    match = re.search(
        rf'^{key}:\s*"?([^"\n]+)"?\s*$',
        config_path.read_text(encoding="utf-8"),
        re.M,
    )
    if match:
        return match.group(1).strip()
    return None


def read_project_label(project_path: Path) -> str | None:
    return _read_config_value(project_path, "label")


def read_project_color(project_path: Path) -> str | None:
    """Return the project's label color.

    Uses the configured `color` if present, otherwise falls back to the
    built-in palette keyed by label name.
    """
    configured = _read_config_value(project_path, "color")
    if configured:
        return configured
    label = read_project_label(project_path)
    return LABEL_COLORS.get(label) if label else None


def read_project_short_name(project_path: Path) -> str | None:
    """Return the configured short name, truncated to a maximum of 4 characters."""
    value = _read_config_value(project_path, "short_name")
    if value:
        return value[:4]
    return None


def compute_short_name(name: str, configured_short_name: str | None = None) -> str:
    """Compute a short name for the collapsed sidebar.

    Rules:
    - If a short name is configured, use it (max 4 characters).
    - Otherwise, if the name has multiple words, use 1 character from each word.
    - Otherwise, use the first 4 characters of the single word.
    """
    if configured_short_name:
        return configured_short_name[:4]
    words = [word for word in re.split(r"[^a-zA-Z0-9]+", name) if word]
    if len(words) > 1:
        return "".join(word[0].upper() for word in words)[:4]
    if words:
        return words[0][:4].upper()
    return name[:4].upper()
