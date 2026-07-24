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
- macOS or Linux

## Install

```bash
git clone git@github.com:burgbart/dashboard-md-launcher.git
cd dashboard-md-launcher
chmod +x bin/*

ln -sf "$(pwd)/bin/dashboard-server" ~/.local/bin/dashboard-server
ln -sf "$(pwd)/bin/dashboard-hub" ~/.local/bin/dashboard-hub
ln -sf "$(pwd)/bin/dash" ~/.local/bin/dash
```

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

## Commands

| Command | Purpose |
|---------|---------|
| `dashboard-server` | Run the hub UI on port 17686 |
| `dashboard-hub add NAME PATH` | Register a project with `backlog/config.yml` |
| `dashboard-hub list` | List configured projects and running status |
| `dashboard-hub open ID` | Open Backlog browser, starting it if needed |
| `dashboard-hub remove ID` | Remove from config |
| `dash [PATH]` | Run `backlog browser` in the current or given project |

## Config

| File | Purpose |
|------|---------|
| `~/.config/dashboard-hub/dashboards.json` | Registered projects |
| `~/.local/share/dashboard-hub/instances.json` | Running browser instances |

Example config:

```json
{
  "hub": { "host": "127.0.0.1", "port": 17686 },
  "portRange": [17687, 17799],
  "dashboards": [
    {
      "id": "my-project",
      "name": "My Project",
      "path": "/home/you/projects/my-project",
      "description": "Optional note"
    }
  ]
}
```

Each project's `backlog/config.yml` may set `default_port` (Backlog.md default: 6420). If that port is busy, the hub picks the next free port in `portRange`.

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
