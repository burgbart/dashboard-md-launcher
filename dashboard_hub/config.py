from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


def _app_dirs() -> tuple[Path, Path]:
    """Return (config_dir, state_dir) for the current platform."""
    if sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        local_appdata = Path(
            os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        )
        return appdata / "dashboard-hub", local_appdata / "dashboard-hub"
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    data_home = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return config_home / "dashboard-hub", data_home / "dashboard-hub"


CONFIG_DIR, STATE_DIR = _app_dirs()
CONFIG_PATH = CONFIG_DIR / "dashboards.json"

DEFAULT_CONFIG = {
    "hub": {"host": "127.0.0.1", "port": 17686},
    "portRange": [49152, 49299],
    "dashboards": [],
}


@dataclass
class HubSettings:
    host: str = "127.0.0.1"
    port: int = 17686


@dataclass
class DashboardEntry:
    id: str
    name: str
    path: Path
    description: str = ""
    port: int | None = None

    def to_dict(self) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "path": str(self.path),
            "description": self.description,
        }
        if self.port is not None:
            data["port"] = self.port
        return data

    @classmethod
    def from_dict(cls, data: dict) -> DashboardEntry:
        return cls(
            id=data["id"],
            name=data["name"],
            path=Path(os.path.expanduser(data["path"])).resolve(),
            description=data.get("description", ""),
            port=int(data["port"]) if data.get("port") is not None else None,
        )


@dataclass
class AppConfig:
    hub: HubSettings = field(default_factory=HubSettings)
    port_range: tuple[int, int] = (49152, 49299)
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
        port_range = data.get("portRange", [49152, 49299])
        return cls(
            hub=HubSettings(
                host=hub_data.get("host", "127.0.0.1"),
                port=int(hub_data.get("port", 17686)),
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
