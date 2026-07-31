---
id: decision-1
title: 'Long-term UI direction: keep Backlog.md format, possibly leave its front-end'
date: '2026-07-31 19:58'
status: accepted
---
## Context

The hub currently depends on the external `backlog` CLI in two ways: dashboards
are rendered by spawning `backlog browser` per project (embedded via iframe),
and Backlog.md itself shells out to `git`. The desktop app (TASK-18, TASK-19)
wraps this unchanged.

During TASK-17/TASK-18 we discussed making the app self-contained. Options were
bundling or downloading the backlog binary (short-term fixes) versus option 3
from doc-1: stop using `backlog browser` entirely and render boards in the hub
from the Backlog.md data (`backlog/tasks/`, `backlog/config.yml`).

See also: doc-1 (Run all dashboards under a single server), doc-2 (Desktop
version research).

## Decision

- **Short term (now): leave as is.** The hub keeps treating `backlog browser`
  as an external binary that is spawned and embedded. No binary bundling or
  download-on-first-run work is started.
- **Long term direction:** we may move away from the Backlog.md *front-end*
  (the `backlog browser` UI) while **staying on the Backlog.md *data format***
  (markdown tasks, `backlog/config.yml`, the CLI workflow). That would mean the
  hub renders boards itself — doc-1 option 3 — giving a fully self-contained
  app and a single server without child processes.

## Consequences

- The `backlog` CLI (and `git`, which Backlog.md uses internally) remain
  documented prerequisites of the app for now.
- Any work toward self-containment should go toward the in-hub rendering
  direction rather than binary bundling, since that is the likely end state.
- If we ever pursue it, in-hub rendering is a large, separate effort with
  feature-drift risk against future Backlog.md versions; it needs its own
  spike before commitment.

## Decision



## Consequences

