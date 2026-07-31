---
id: TASK-14
title: 'Cross-platform support: Windows and Linux'
status: Done
assignee: []
created_date: '2026-07-31 12:40'
labels: []
dependencies: []
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make dashboard-md-launcher work on Windows and Linux in addition to macOS. Areas to review: process spawning/killing in dashboard_hub/backlog_browser.py and registry.py (ps/kill usage, signal handling), path handling (config/state dirs under ~/.config and ~/.local/share should use platform-appropriate locations, e.g. %APPDATA% on Windows), shell scripts in bin/ (need .cmd/.ps1 equivalents or documented alternatives for Windows), and any macOS-only assumptions in the hub server UI. Verify: python3 -m dashboard_hub list works, server starts, and start/stop of dashboards works on both platforms.
<!-- SECTION:DESCRIPTION:END -->
