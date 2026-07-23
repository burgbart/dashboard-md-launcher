from __future__ import annotations

import json
import os
import re
import signal
import socket
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import STATE_DIR, ensure_dirs

REGISTRY_PATH = STATE_DIR / "instances.json"


@dataclass
class RunningInstance:
    id: str
    name: str
    path: str
    url: str
    port: int
    pid: int
    started_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "url": self.url,
            "port": self.port,
            "pid": self.pid,
            "startedAt": self.started_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> RunningInstance:
        return cls(
            id=data["id"],
            name=data["name"],
            path=data["path"],
            url=data["url"],
            port=int(data["port"]),
            pid=int(data["pid"]),
            started_at=data["startedAt"],
        )


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_registry() -> list[RunningInstance]:
    ensure_dirs()
    if not REGISTRY_PATH.exists():
        return []
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return [RunningInstance.from_dict(item) for item in data]


def save_registry(instances: list[RunningInstance]) -> None:
    ensure_dirs()
    REGISTRY_PATH.write_text(
        json.dumps([item.to_dict() for item in instances], indent=2) + "\n",
        encoding="utf-8",
    )


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def port_open(host: str, port: int, timeout: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def instance_healthy(instance: RunningInstance, host: str = "127.0.0.1") -> bool:
    if not pid_alive(instance.pid):
        return False
    return port_open(host, instance.port)


def prune_registry(host: str = "127.0.0.1") -> list[RunningInstance]:
    alive = [item for item in load_registry() if instance_healthy(item, host)]
    save_registry(alive)
    return alive


def register_instance(instance: RunningInstance) -> None:
    instances = prune_registry()
    instances = [item for item in instances if item.id != instance.id]
    instances.append(instance)
    save_registry(instances)


def unregister_instance(dashboard_id: str) -> None:
    instances = [item for item in load_registry() if item.id != dashboard_id]
    save_registry(instances)


def find_instance(dashboard_id: str) -> RunningInstance | None:
    for item in prune_registry():
        if item.id == dashboard_id:
            return item
    return None


def find_free_port(start: int, end: int, host: str = "127.0.0.1") -> int:
    used = {item.port for item in load_registry()}
    for port in range(start, end + 1):
        if port in used:
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((host, port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No free port available in range {start}-{end}")


def wait_for_instance(
    dashboard_id: str,
    timeout: float = 8.0,
    poll_interval: float = 0.2,
) -> RunningInstance | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        instance = find_instance(dashboard_id)
        if instance:
            return instance
        time.sleep(poll_interval)
    return None


def terminate_instance(instance: RunningInstance) -> None:
    if pid_alive(instance.pid):
        try:
            os.kill(instance.pid, signal.SIGTERM)
        except OSError:
            pass
