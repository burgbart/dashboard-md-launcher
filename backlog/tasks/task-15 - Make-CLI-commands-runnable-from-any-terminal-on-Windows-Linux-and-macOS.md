---
id: TASK-15
title: Make CLI commands runnable from any terminal on Windows, Linux, and macOS
status: Done
assignee: []
created_date: '2026-07-31 16:45'
labels: []
dependencies: []
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`dashboard-server` (and `dashboard-hub`, `dash`) should be executable from any
directory in PowerShell, a Linux terminal, or a macOS terminal — not just from
inside the repo. Document the install steps in README.md and provide a real
install path for Windows (the previous `$env:Path += ...` snippet only lasted
for the current PowerShell session). Verify the commands resolve on PATH from
a fresh shell after installing.
<!-- SECTION:DESCRIPTION:END -->

## Resolution

<!-- SECTION:DESCRIPTION:BEGIN -->
- macOS/Linux: unchanged symlink approach into `~/.local/bin`, documented with
  the `PATH` export needed in `~/.bashrc`/`~/.zshrc` if not already present.
- Windows: added `bin/install.ps1`, which generates `.cmd` shims (with the
  repo's absolute path baked in) into `%USERPROFILE%\.local\bin` and adds that
  directory to the User `PATH` permanently via
  `[Environment]::SetEnvironmentVariable(..., "User")`, so it persists across
  new terminals without requiring admin rights or Developer Mode symlinks.
- README.md updated with per-platform install steps and a verification step.
<!-- SECTION:DESCRIPTION:END -->
