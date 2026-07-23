# dashboard-md-launcher

Browse, search, and launch local [`dashboard.md`](dashboard.md) viewers across projects from one hub page.

Each project can keep a simple markdown status board. This tool registers those projects in a local config file, shows which dashboards are running, and starts them on demand.

## Features

- Hub UI with search across name, id, path, description, and status
- Config-based registry of dashboards on your machine
- Start-on-click: opens a running dashboard or launches it first
- Per-project viewer with live reload when `dashboard.md` changes
- No pip dependencies — Python 3 standard library only

## Requirements

- Python 3.9+
- macOS or Linux (Windows may work; primarily tested on macOS)

## Install

Clone the repository and add the commands to your `PATH`:

```bash
git clone git@github.com:burgbart/dashboard-md-launcher.git
cd dashboard-md-launcher
chmod +x bin/*

ln -sf "$(pwd)/bin/dashboard-server" ~/.local/bin/dashboard-server
ln -sf "$(pwd)/bin/dashboard-hub" ~/.local/bin/dashboard-hub
ln -sf "$(pwd)/bin/dash" ~/.local/bin/dash
```

Ensure `~/.local/bin` is on your `PATH`.

Optional hosts entry for a nicer URL:

```text
127.0.0.1 dashboards.local
```

Then open `http://dashboards.local:8786/dashboards/`.

## Quick start

1. Add a `dashboard.md` file to a project.
2. Register the project:

```bash
dashboard-hub add "My Project" ~/path/to/project
dashboard-hub list
```

3. Start the hub:

```bash
dashboard-server
```

4. Open the hub in your browser, search, and click **Start & Open**.

## Commands

| Command | Purpose |
|---------|---------|
| `dashboard-server` | Run the hub UI on port 8786 |
| `dashboard-hub add NAME PATH` | Register a project with `dashboard.md` |
| `dashboard-hub list` | List configured dashboards and running status |
| `dashboard-hub open ID` | Open a dashboard, starting it if needed |
| `dashboard-hub remove ID` | Remove from config |
| `dash [PATH]` | Run `dashboard.md` in the current or given project |

## Config

User-specific files are stored outside the repository:

| File | Purpose |
|------|---------|
| `~/.config/dashboard-hub/dashboards.json` | Registered dashboards |
| `~/.local/share/dashboard-hub/instances.json` | Running viewer instances |

Example config:

```json
{
  "hub": { "host": "127.0.0.1", "port": 8786 },
  "portRange": [8787, 8899],
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

## How it works

1. `dashboard-server` serves a local hub page.
2. The hub reads configured dashboards and checks which viewers are running.
3. Clicking **Start & Open** spawns a viewer process if needed, then opens its URL.
4. Each viewer serves `dashboard.md` from the project directory and polls for file changes.

## Project layout

```text
dashboard-md-launcher/
├── bin/                 # CLI launchers
├── dashboard_hub/       # Python package
├── dashboard.md         # Example dashboard file
├── CHANGELOG.md
├── LICENSE
└── README.md
```

## License

MIT — see [LICENSE](LICENSE).
