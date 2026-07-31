from __future__ import annotations

import json
import os
import re
import signal
import shutil
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import STATE_DIR, ensure_dirs

WINDOWS = sys.platform == "win32"

if WINDOWS:
    import msvcrt
else:
    import fcntl

REGISTRY_PATH = STATE_DIR / "instances.json"
REGISTRY_LOCK_PATH = STATE_DIR / ".instances.lock"


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


def _acquire_lock(lock_file) -> None:
    if WINDOWS:
        lock_file.seek(0)
        while True:
            try:
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                time.sleep(0.05)
    else:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)


def _release_lock(lock_file) -> None:
    if WINDOWS:
        lock_file.seek(0)
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


@contextmanager
def _registry_lock():
    """Serialize registry read-modify-write across hub threads and CLI processes."""
    ensure_dirs()
    REGISTRY_LOCK_PATH.touch(exist_ok=True)
    if WINDOWS and REGISTRY_LOCK_PATH.stat().st_size == 0:
        # msvcrt.locking needs at least one byte to lock.
        REGISTRY_LOCK_PATH.write_bytes(b"\0")
    mode = "r+b" if WINDOWS else "w"
    with open(REGISTRY_LOCK_PATH, mode) as lock_file:
        _acquire_lock(lock_file)
        try:
            yield
        finally:
            _release_lock(lock_file)


def _healthy_instances(host: str = "127.0.0.1") -> list[RunningInstance]:
    return [item for item in load_registry() if instance_healthy(item, host)]


def _win_pid_alive(pid: int) -> bool:
    import ctypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    try:
        exit_code = ctypes.c_ulong()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return False
        return exit_code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if WINDOWS:
        return _win_pid_alive(pid)
    try:
        waited_pid, _ = os.waitpid(pid, os.WNOHANG)
        if waited_pid == pid:
            return False
    except ChildProcessError:
        pass
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


def _win_process_parents() -> dict[int, int]:
    """Return {pid: parent_pid} for all processes via a Toolhelp32 snapshot."""
    import ctypes
    from ctypes import wintypes

    TH32CS_SNAPPROCESS = 0x00000002
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_char * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot in (0, INVALID_HANDLE_VALUE):
        return {}

    parents: dict[int, int] = {}
    try:
        entry = PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
        if not kernel32.Process32First(snapshot, ctypes.byref(entry)):
            return {}
        while True:
            parents[entry.th32ProcessID] = entry.th32ParentProcessID
            if not kernel32.Process32Next(snapshot, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snapshot)
    return parents


def process_tree_pids(root_pid: int) -> set[int]:
    """Return a process and all of its descendants."""
    children: dict[int, list[int]] = {}
    if WINDOWS:
        for pid, parent in _win_process_parents().items():
            children.setdefault(parent, []).append(pid)
    else:
        try:
            result = subprocess.run(
                ["ps", "-axo", "pid=,ppid="],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError):
            return {root_pid} if pid_alive(root_pid) else set()

        for line in result.stdout.splitlines():
            try:
                pid_text, parent_text = line.split()
                pid, parent = int(pid_text), int(parent_text)
            except (ValueError, TypeError):
                continue
            children.setdefault(parent, []).append(pid)

    tree: set[int] = set()
    pending = [root_pid]
    while pending:
        pid = pending.pop()
        if pid in tree:
            continue
        tree.add(pid)
        pending.extend(children.get(pid, ()))
    return tree


def process_cwd(pid: int) -> Path | None:
    proc_cwd = Path("/proc") / str(pid) / "cwd"
    try:
        return proc_cwd.resolve(strict=True)
    except OSError:
        pass

    if not shutil.which("lsof"):
        return None
    try:
        result = subprocess.run(
            ["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    for line in result.stdout.splitlines():
        if line.startswith("n"):
            return Path(line[1:]).resolve()
    return None


def _win_listening_pids(port: int) -> set[int]:
    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return set()

    pids: set[int] = set()
    target = str(port)
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) < 5 or fields[0] != "TCP":
            continue
        local_addr, state, pid_text = fields[1], fields[3], fields[-1]
        if state != "LISTENING":
            continue
        if local_addr.rsplit(":", 1)[-1] != target:
            continue
        try:
            pids.add(int(pid_text))
        except ValueError:
            continue
    return pids


def listening_pids(port: int) -> set[int]:
    """Return PIDs listening on a TCP port using lsof, Linux procfs, or netstat."""
    if WINDOWS:
        return _win_listening_pids(port)
    if shutil.which("lsof"):
        try:
            result = subprocess.run(
                ["lsof", "-nP", "-t", f"-iTCP:{port}", "-sTCP:LISTEN"],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            return set()
        return {
            int(line)
            for line in result.stdout.splitlines()
            if line.strip().isdigit()
        }

    socket_inodes: set[str] = set()
    for table in (Path("/proc/net/tcp"), Path("/proc/net/tcp6")):
        try:
            lines = table.read_text(encoding="utf-8").splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            fields = line.split()
            if len(fields) > 9 and fields[3] == "0A":
                try:
                    local_port = int(fields[1].rsplit(":", 1)[1], 16)
                except (ValueError, IndexError):
                    continue
                if local_port == port:
                    socket_inodes.add(fields[9])

    owners: set[int] = set()
    proc = Path("/proc")
    if not socket_inodes or not proc.exists():
        return owners
    for process_dir in proc.iterdir():
        if not process_dir.name.isdigit():
            continue
        fd_dir = process_dir / "fd"
        try:
            descriptors = list(fd_dir.iterdir())
        except OSError:
            continue
        for descriptor in descriptors:
            try:
                target = os.readlink(descriptor)
            except OSError:
                continue
            match = re.fullmatch(r"socket:\[(\d+)\]", target)
            if match and match.group(1) in socket_inodes:
                owners.add(int(process_dir.name))
                break
    return owners


def process_owns_port(root_pid: int, port: int, project_path: str | Path) -> bool:
    """Return True if a descendant of root_pid is listening on port.

    When the process cwd cannot be determined (e.g. no /proc, lsof, or PEB
    access on Windows), fall back to trusting tree membership alone, since
    root_pid is a process we spawned ourselves for this project.
    """
    expected_path = Path(project_path).resolve()
    tree = process_tree_pids(root_pid)
    for pid in listening_pids(port):
        if pid not in tree:
            continue
        cwd = process_cwd(pid)
        if cwd is None or cwd == expected_path:
            return True
    return False


def port_serves_project(port: int, project_path: str | Path) -> bool:
    """Return True when a listener on port is running from the project directory."""
    expected_path = Path(project_path).resolve()
    for pid in listening_pids(port):
        if process_cwd(pid) == expected_path:
            return True
    return False


def instance_healthy(instance: RunningInstance, host: str = "127.0.0.1") -> bool:
    if not port_open(host, instance.port):
        return False
    if pid_alive(instance.pid) and process_owns_port(
        instance.pid, instance.port, instance.path
    ):
        return True
    return port_serves_project(instance.port, instance.path)


def prune_registry(host: str = "127.0.0.1") -> list[RunningInstance]:
    with _registry_lock():
        alive = _healthy_instances(host)
        save_registry(alive)
        return alive


def register_instance(instance: RunningInstance, host: str = "127.0.0.1") -> None:
    with _registry_lock():
        instances = _healthy_instances(host)
        instances = [item for item in instances if item.id != instance.id]
        instances.append(instance)
        save_registry(instances)


def unregister_instance(dashboard_id: str) -> None:
    with _registry_lock():
        instances = [item for item in load_registry() if item.id != dashboard_id]
        save_registry(instances)


def find_instance(dashboard_id: str, host: str = "127.0.0.1") -> RunningInstance | None:
    with _registry_lock():
        alive = _healthy_instances(host)
        save_registry(alive)
        for item in alive:
            if item.id == dashboard_id:
                return item
        return None


def list_instances(host: str = "127.0.0.1") -> list[RunningInstance]:
    """Prune stale entries once and return all healthy instances."""
    return prune_registry(host)


def find_free_port(start: int, end: int, host: str = "127.0.0.1") -> int:
    with _registry_lock():
        used = {item.port for item in _healthy_instances(host)}
    for port in range(start, end + 1):
        if port in used or port_open(host, port) or listening_pids(port):
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
    terminate_process_tree(instance.pid)


def terminate_process_tree(root_pid: int, timeout: float = 5.0) -> None:
    """Terminate descendants before their launcher so no listener is orphaned."""
    pids = process_tree_pids(root_pid)
    if not pids:
        return
    for pid in sorted(pids - {root_pid}, reverse=True):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    if root_pid in pids:
        try:
            os.kill(root_pid, signal.SIGTERM)
        except OSError:
            pass

    kill_signal = getattr(signal, "SIGKILL", signal.SIGTERM)
    deadline = time.time() + timeout
    while time.time() < deadline and any(pid_alive(pid) for pid in pids):
        time.sleep(0.05)
    for pid in pids:
        if pid_alive(pid):
            try:
                os.kill(pid, kill_signal)
            except OSError:
                pass
