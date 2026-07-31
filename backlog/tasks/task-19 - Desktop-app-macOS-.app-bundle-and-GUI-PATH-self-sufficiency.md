---
id: TASK-19
title: 'Desktop app: macOS .app bundle and GUI PATH self-sufficiency'
status: Done
assignee:
  - '@kimi'
created_date: '2026-07-31 19:48'
updated_date: '2026-07-31 19:48'
labels: []
dependencies: []
type: feature
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Retroactive tracking for work completed 2026-07-31, following TASK-18. Two pieces:
1. Extend packaging/dashboard-desktop.spec with a PyInstaller BUNDLE step so the macOS build produces a real "Dashboard Hub.app" (bundle id com.dashboardhub.desktop) that can be dragged into /Applications.
2. Bugfix: when launched from Finder/Spotlight/open, the app inherits launchd PATH (/usr/bin:/bin:/usr/sbin:/sbin), so "backlog" (and "node", needed by the backlog shim) were not found and opening a dashboard failed with "backlog CLI not found on PATH". Fix: augment_path() in dashboard_hub/desktop.py appends common CLI locations (/opt/homebrew/bin, /usr/local/bin, ~/.local/bin; %APPDATA%\npm on Windows) to the process PATH at startup.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 macOS build produces dist/Dashboard Hub.app that launches via open/Finder and serves the hub
- [x] #2 GUI-launched app can start a backlog dashboard without a shell-provided PATH
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verification (macOS arm64):
- 'open dist/Dashboard Hub.app' launched via LaunchServices; hub served 200; Cmd+W closed it and freed port 17686 (teardown ran). Cmd+Q is not wired by pywebview — documented in README.
- Bug reproduction: ps eww on the GUI-launched process showed PATH=/usr/bin:/bin:/usr/sbin:/sbin and POST /api/dashboards/<id>/open failed with 'backlog CLI not found on PATH'.
- augment_path() unit check with PATH=/usr/bin:/bin:/usr/sbin:/sbin: shutil.which finds both /opt/homebrew/bin/backlog and /opt/homebrew/bin/node after augmentation.
- Rebuilt .app, relaunched via open: POST /api/dashboards/trmnl-family-plugin/open returned started:true and the board served 200 on 49164.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped Dashboard Hub.app via a BUNDLE step in packaging/dashboard-desktop.spec and fixed GUI-launch PATH handling with augment_path() in dashboard_hub/desktop.py (adds /opt/homebrew/bin, /usr/local/bin, ~/.local/bin; %APPDATA%\npm on Windows). Verified: app launches via open, starts a dashboard with no shell PATH (started:true, board 200), closes cleanly via Cmd+W/close button with full teardown.
<!-- SECTION:FINAL_SUMMARY:END -->
