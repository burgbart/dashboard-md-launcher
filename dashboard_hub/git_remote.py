from __future__ import annotations

import re
import subprocess
from pathlib import Path

_GITHUB_SSH_RE = re.compile(r"^git@github\.com:(?P<owner>[^/]+)/(?P<repo>.+?)(?:\.git)?$")
_GITHUB_SSH_URL_RE = re.compile(r"^ssh://git@github\.com/(?P<owner>[^/]+)/(?P<repo>.+?)(?:\.git)?$")
_GITHUB_HTTPS_RE = re.compile(
    r"^https?://(?:www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>.+?)(?:\.git)?(?:/.*)?$"
)


def get_git_origin_url(project_path: Path) -> str | None:
    path = project_path.resolve()
    if not path.is_dir():
        return None

    try:
        result = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            if url:
                return url
    except (OSError, subprocess.SubprocessError):
        pass

    config_path = _git_config_path(path)
    if config_path is None or not config_path.is_file():
        return None

    try:
        return _parse_origin_from_config(config_path.read_text(encoding="utf-8"))
    except OSError:
        return None


def _git_config_path(project_path: Path) -> Path | None:
    git_path = project_path / ".git"
    if git_path.is_dir():
        return git_path / "config"
    if git_path.is_file():
        gitdir = _read_gitdir(git_path)
        if gitdir is not None:
            return gitdir / "config"
    return None


def _read_gitdir(git_file: Path) -> Path | None:
    try:
        text = git_file.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        if line.startswith("gitdir:"):
            gitdir = Path(line.split(":", 1)[1].strip())
            if not gitdir.is_absolute():
                gitdir = (git_file.parent / gitdir).resolve()
            return gitdir
    return None


def _parse_origin_from_config(text: str) -> str | None:
    in_origin = False
    for line in text.splitlines():
        line = line.strip()
        if line == '[remote "origin"]':
            in_origin = True
            continue
        if in_origin:
            if line.startswith("[") and line.endswith("]"):
                break
            if line.startswith("url ="):
                return line.split("=", 1)[1].strip()
    return None


def normalize_github_url(remote_url: str) -> str | None:
    remote_url = remote_url.strip()
    if not remote_url:
        return None

    for pattern in (_GITHUB_SSH_RE, _GITHUB_SSH_URL_RE, _GITHUB_HTTPS_RE):
        match = pattern.match(remote_url)
        if match:
            owner = match.group("owner")
            repo = match.group("repo")
            if repo.endswith(".git"):
                repo = repo[:-4]
            return f"https://github.com/{owner}/{repo}"

    return None


def get_github_url(project_path: Path) -> str | None:
    remote = get_git_origin_url(project_path)
    if not remote:
        return None
    return normalize_github_url(remote)
