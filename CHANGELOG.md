# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-23

### Added

- `dashboard-server` hub UI at `/dashboards/` with search and live status
- Config-driven dashboard registry (`dashboard-hub add`, `list`, `remove`, `open`)
- Per-project `dashboard.md` viewer with live reload (`dash`)
- On-demand launch: hub starts a viewer when you open a stopped dashboard
- Runtime registry for tracking active viewer instances and ports
- Zero third-party dependencies (Python 3 standard library only)

[0.1.0]: https://github.com/burgbart/dashboard-md-launcher/releases/tag/v0.1.0
