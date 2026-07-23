# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-07-23

### Added

- Collapsible sidebar project picker in the hub UI
- In-page dashboard viewing via embedded iframe with `?embed=1` chrome-less viewer mode
- Deep links via `?id=<dashboard-id>` and Enter-to-select when search has one match
- Reload and open-in-tab actions in the main header

### Changed

- Hub layout is now a split sidebar + main pane instead of a card list

## [0.1.0] - 2026-07-23

### Added

- `dashboard-server` hub UI at `/dashboards/` with search and live status
- Config-driven dashboard registry (`dashboard-hub add`, `list`, `remove`, `open`)
- Per-project `dashboard.md` viewer with live reload (`dash`)
- On-demand launch: hub starts a viewer when you open a stopped dashboard
- Runtime registry for tracking active viewer instances and ports
- Zero third-party dependencies (Python 3 standard library only)

[0.2.0]: https://github.com/burgbart/dashboard-md-launcher/releases/tag/v0.2.0
[0.1.0]: https://github.com/burgbart/dashboard-md-launcher/releases/tag/v0.1.0
