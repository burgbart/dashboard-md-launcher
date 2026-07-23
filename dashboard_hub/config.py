from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "dashboard-hub"
CONFIG_PATH = CONFIG_DIR / "dashboards.json"
STATE_DIR = Path.home() / ".local" / "share" / "dashboard-hub"

DEFAULT_CONFIG = {
    "hub": {"host": "127.0.0.1", "port": 8786},
    "portRange": [8787, 8899],
    "dashboards": [],
}


@dataclass
class HubSettings:
    host: str = "127.0.0.1"
    port: int = 8786


@dataclass
class DashboardEntry:
    id: str
    name: str
    path: Path
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "path": str(self.path),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DashboardEntry:
        return cls(
            id=data["id"],
            name=data["name"],
            path=Path(os.path.expanduser(data["path"])).resolve(),
            description=data.get("description", ""),
        )


@dataclass
class AppConfig:
    hub: HubSettings = field(default_factory=HubSettings)
    port_range: tuple[int, int] = (8787, 8899)
    dashboards: list[DashboardEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "hub": {"host": self.hub.host, "port": self.hub.port},
            "portRange": list(self.port_range),
            "dashboards": [entry.to_dict() for entry in self.dashboards],
        }

    @classmethod
    def from_dict(cls, data: dict) -> AppConfig:
        hub_data = data.get("hub", {})
        port_range = data.get("portRange", [8787, 8899])
        return cls(
            hub=HubSettings(
                host=hub_data.get("host", "127.0.0.1"),
                port=int(hub_data.get("port", 8786)),
            ),
            port_range=(int(port_range[0]), int(port_range[1])),
            dashboards=[DashboardEntry.from_dict(item) for item in data.get("dashboards", [])],
        )


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "dashboard"


def ensure_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> AppConfig:
    ensure_dirs()
    if not CONFIG_PATH.exists():
        save_config(AppConfig.from_dict(DEFAULT_CONFIG))
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return AppConfig.from_dict(data)


def save_config(config: AppConfig) -> None:
    ensure_dirs()
    CONFIG_PATH.write_text(
        json.dumps(config.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )


def find_dashboard(config: AppConfig, dashboard_id: str) -> DashboardEntry | None:
    for entry in config.dashboards:
        if entry.id == dashboard_id:
            return entry
    return None
