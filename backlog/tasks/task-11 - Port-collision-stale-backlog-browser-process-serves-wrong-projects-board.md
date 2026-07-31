---
id: TASK-11
title: 'Port collision: stale backlog browser process serves wrong project''s board'
status: Done
assignee: []
created_date: '2026-07-24 14:43'
labels:
  - dashboard-hub
dependencies: []
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Problem

Registered projects can share the same Backlog.md default_port (6420) when
their backlog/config.yml doesn't override it. Observed: both `mobdevops` and
`wealth-calibration` were left at the Backlog.md default of 6420.

A `backlog browser --port 6420` process for mobdevops (pid 5836, started
10:44AM) was already bound to that port. When the hub later started a
browser for wealth-calibration on the same port, the new process failed to
bind (port already in use) but:

- dashboard-hub did not detect the bind failure
- instances.json was still updated to record wealth-calibration -> port 6420
- the hub happily iframed http://127.0.0.1:6420, which was actually still
  served by the old mobdevops process

Result: opening "Wealth Calibration" in the hub showed mobdevops's tasks
(e.g. TASK-1 "Define label taxonomy for task categorization").

Also found several other orphaned `backlog browser` processes still running
on ports 6420/17687/17690 from earlier sessions today that were never
cleaned up (e.g. pids 85465/85471, 94622/94627/94598/94591, 32715/98447).

## Root causes

1. No collision detection: dashboard-hub doesn't check whether a
   default_port is already claimed by another registered project before
   assigning/starting on it.
2. No bind verification: after spawning `backlog browser --port X`,
   dashboard-hub doesn't confirm the new process is actually the one
   listening on X (e.g. by checking the process's cwd against the project
   path, or verifying the PID that owns the LISTEN socket).
3. No process lifecycle cleanup: repeated start/reload cycles leave orphaned
   `backlog browser` processes running instead of stopping the previous one
   first, so old processes keep squatting on ports indefinitely.

## Proposed fix

- When registering/starting a project, check all registered projects'
  backlog/config.yml default_port values (dashboard_hub/config.py or
  project_config.py) and auto-assign a free port from portRange if there's a
  collision, persisting the choice so it's stable across restarts.
- After spawning `backlog browser`, verify the actual LISTEN owner on the
  chosen port (e.g. via lsof/psutil equivalent) matches the spawned PID and
  its cwd matches the project path before writing to instances.json /
  reporting success to the user. Retry on a different port if verification
  fails.
- Before starting a project, check dashboard_hub/registry.py's
  instances.json plus real OS process state for existing `backlog browser`
  processes bound to the target port; kill orphaned ones (or reuse them only
  if they truly belong to the same project path) instead of spawning a
  duplicate.
- Add a `dashboard-hub doctor` (or similar) command to list port collisions
  across registered projects and clean up orphaned backlog browser
  processes.

## Immediate workaround (not a code fix)

- Kill stale duplicate `backlog browser` processes.
- Set a unique `default_port` in each project's backlog/config.yml to avoid
  the 6420 collision (e.g. wealth-calibration -> 6424).
<!-- SECTION:DESCRIPTION:END -->
