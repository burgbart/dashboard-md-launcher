# dashboard-md-launcher

Browse, search, and launch [Backlog.md](https://github.com/MrLesk/Backlog.md) browser UIs across projects from one hub page.

Each project uses a `backlog/` folder (from `backlog init`). The hub embeds the real Backlog kanban board and starts `backlog browser` on demand.

## Features

- Hub UI with collapsible sidebar, search, and in-page Backlog board viewing
- Config-based registry of Backlog.md projects on your machine
- Start-on-click: launches `backlog browser` if not already running
- Reads `default_port` from each project's `backlog/config.yml` when available
- Project labels from `dashboard-hub/config.yml` with sidebar filter chips
- Requires the `backlog` CLI (`npm i -g backlog.md` or `brew install backlog-md`)

## Requirements

- Python 3.9+
- [Backlog.md CLI](https://github.com/MrLesk/Backlog.md) on your `PATH`
- macOS, Linux, or Windows

## Install

These steps make `dashboard-server`, `dashboard-hub`, and `dash` runnable from any
terminal — any directory, any new shell — on macOS, Linux, or Windows, by installing
small launcher shims into `~/.local/bin` (`%USERPROFILE%\.local\bin` on Windows) and
ensuring that directory is on your `PATH`.

macOS / Linux (bash/zsh):

```bash
git clone git@github.com:burgbart/dashboard-md-launcher.git
cd dashboard-md-launcher
chmod +x bin/*

mkdir -p ~/.local/bin
ln -sf "$(pwd)/bin/dashboard-server" ~/.local/bin/dashboard-server
ln -sf "$(pwd)/bin/dashboard-hub" ~/.local/bin/dashboard-hub
ln -sf "$(pwd)/bin/dash" ~/.local/bin/dash

# Make sure ~/.local/bin is on PATH (add to ~/.bashrc or ~/.zshrc if not already):
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

Windows (PowerShell):

```powershell
git clone git@github.com:burgbart/dashboard-md-launcher.git
cd dashboard-md-launcher

# Installs shims into %USERPROFILE%\.local\bin and adds that folder to your
# User PATH permanently (persists across new terminal sessions).
.\bin\install.ps1
```

Open a new terminal after either install step so the updated `PATH` takes effect.
Verify with `dashboard-server --help` (or `Get-Command dashboard-server` on Windows)
from any directory.

Optional hosts entry:

```text
127.0.0.1 dashboards.local
```

Then open `http://dashboards.local:17686/dashboards/`.

## Quick start

1. Initialize Backlog.md in a project:

```bash
cd ~/path/to/project
backlog init "My Project"
```

2. Register the project:

```bash
dashboard-hub add "My Project" ~/path/to/project
dashboard-hub list
```

3. Start the hub:

```bash
dashboard-server
```

4. Pick a project in the sidebar — the Backlog board loads in the main pane.

## Desktop app

`dashboard-desktop` runs the same hub UI in a native OS webview window instead
of a browser tab. Closing the window shuts the hub down and stops all running
dashboards.

Run from a source checkout (requires `pip install pywebview`):

```bash
dashboard-desktop
```

Or build a single-file executable — no installation step, just download and run:

```bash
python3 -m venv .venv && .venv/bin/pip install pywebview pyinstaller
.venv/bin/pyinstaller packaging/dashboard-desktop.spec --noconfirm
# output: dist/dashboard-desktop (dist/dashboard-desktop.exe on Windows)
# macOS additionally: dist/Dashboard Hub.app — drag it into /Applications
```

PyInstaller does not cross-compile: the Windows and Linux builds must run on
Windows and Linux respectively. To make the app "really installed" on each
platform:

- **macOS**: `Dashboard Hub.app` (built above) — drag into `/Applications`,
  launch via Spotlight/Launchpad like any app. Optionally wrap it in a `.dmg`
  with [create-dmg](https://github.com/create-dmg/create-dmg) for distribution.
- **Windows**: wrap `dashboard-desktop.exe` in an installer with
  [Inno Setup](https://jrsoftware.org/isinfo.php) or
  [NSIS](https://nsis.sourceforge.io/) to get a Start Menu entry and
  Add/Remove Programs listing.
- **Linux**: package the executable as an
  [AppImage](https://appimage.org/) (with appimagetool) or a `.deb`/`.rpm`;
  AppImage is the closest equivalent to the no-install single file.

Closing the app: click the window's close button or press Cmd+W — this shuts
down the hub and stops all running dashboards. (Cmd+Q is not wired up by
pywebview on macOS.)

Limitations:

- The `backlog` CLI is still required on `PATH`; only the hub is bundled.
- pywebview uses the OS webview: WebView2 (Windows), WKWebView (macOS),
  WebKitGTK (Linux — install `webkit2gtk` via your package manager).
- The executable is unsigned: macOS Gatekeeper and Windows SmartScreen will
  warn on first run (right-click → Open on macOS). Code signing/notarization
  is not set up yet.

## Commands

| Command | Purpose |
|---------|---------|
| `dashboard-server` | Run the hub UI on port 17686 |
| `dashboard-desktop` | Run the hub UI in a native desktop window (requires `pywebview`) |
| `dashboard-hub add NAME PATH` | Register a project with `backlog/config.yml` |
| `dashboard-hub list` | List configured projects and running status |
| `dashboard-hub open ID` | Open Backlog browser, starting it if needed |
| `dashboard-hub remove ID` | Remove from config |
| `dashboard-hub doctor [--clean]` | Find port collisions and stale browser processes |
| `dash [PATH]` | Run `backlog browser` in the current or given project |

## Config

| File | macOS / Linux | Windows |
|------|---------------|---------|
| Registered projects | `~/.config/dashboard-hub/dashboards.json` | `%APPDATA%\dashboard-hub\dashboards.json` |
| Running browser instances | `~/.local/share/dashboard-hub/instances.json` | `%LOCALAPPDATA%\dashboard-hub\instances.json` |

Example config:

```json
{
  "hub": { "host": "127.0.0.1", "port": 17686 },
  "portRange": [49152, 49299],
  "dashboards": [
    {
      "id": "my-project",
      "name": "My Project",
      "path": "/home/you/projects/my-project",
      "description": "Optional note",
      "port": 49152
    }
  ]
}
```

Each project's `backlog/config.yml` may set `default_port` (Backlog.md default: 6420).
The hub stores a stable, unique `port` assignment for each project. If a preferred
port is already assigned or occupied, it picks a free port from `portRange`.

Run `dashboard-hub doctor` to report duplicate defaults, stale registry entries,
and orphaned `backlog browser` processes. Add `--clean` to terminate orphaned
process trees belonging to registered projects.

Optional `dashboard-hub/config.yml` in a project root sets hub metadata (separate from Backlog.md config):

```yaml
label: Personal
```

## How it works

1. `dashboard-server` serves a local hub with a searchable sidebar.
2. Selecting a project runs `backlog browser --no-open --port <port>` if needed.
3. The hub embeds the Backlog web UI in the main pane via iframe.

## Project layout

```text
dashboard-md-launcher/
├── bin/
├── dashboard_hub/
├── backlog/             # this repo's own Backlog.md data
├── CHANGELOG.md
├── LICENSE
└── README.md
```

## License

MIT — see [LICENSE](LICENSE).
