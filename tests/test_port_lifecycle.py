from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dashboard_hub.backlog_browser import choose_port
from dashboard_hub.config import AppConfig, DashboardEntry
from dashboard_hub.registry import instance_healthy, port_serves_project, process_owns_port


class PortAssignmentTests(unittest.TestCase):
    def test_duplicate_backlog_defaults_use_port_range(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first_path = root / "first"
            second_path = root / "second"
            for project_path in (first_path, second_path):
                config_path = project_path / "backlog" / "config.yml"
                config_path.parent.mkdir(parents=True)
                config_path.write_text("default_port: 6420\n", encoding="utf-8")

            first = DashboardEntry("first", "First", first_path)
            second = DashboardEntry("second", "Second", second_path)
            config = AppConfig(
                port_range=(49152, 49299),
                dashboards=[first, second],
            )

            with (
                patch("dashboard_hub.backlog_browser.load_config", return_value=config),
                patch(
                    "dashboard_hub.backlog_browser.find_free_port",
                    side_effect=lambda start, _end, host: start,
                ),
            ):
                self.assertEqual(choose_port(first), 6420)
                self.assertEqual(choose_port(second), 49152)

    def test_assigned_port_round_trips_through_config(self) -> None:
        entry = DashboardEntry(
            id="project",
            name="Project",
            path=Path("/tmp/project"),
            port=49152,
        )

        restored = DashboardEntry.from_dict(entry.to_dict())

        self.assertEqual(restored.port, 49152)


class PortOwnershipTests(unittest.TestCase):
    def test_listener_must_be_descendant_with_matching_cwd(self) -> None:
        project_path = Path("/tmp/project")
        with (
            patch(
                "dashboard_hub.registry.process_tree_pids",
                return_value={100, 101},
            ),
            patch("dashboard_hub.registry.listening_pids", return_value={101}),
            patch(
                "dashboard_hub.registry.process_cwd",
                return_value=project_path.resolve(),
            ),
        ):
            self.assertTrue(process_owns_port(100, 6420, project_path))

    def test_unrelated_listener_is_rejected(self) -> None:
        with (
            patch(
                "dashboard_hub.registry.process_tree_pids",
                return_value={100, 101},
            ),
            patch("dashboard_hub.registry.listening_pids", return_value={999}),
        ):
            self.assertFalse(process_owns_port(100, 6420, "/tmp/project"))


class InstanceHealthTests(unittest.TestCase):
    def test_dead_launcher_stays_healthy_when_port_still_serves_project(self) -> None:
        from dashboard_hub.registry import RunningInstance

        instance = RunningInstance(
            id="project",
            name="Project",
            path="/tmp/project",
            url="http://127.0.0.1:6420/",
            port=6420,
            pid=100,
            started_at="2026-07-24T00:00:00+00:00",
        )
        with (
            patch("dashboard_hub.registry.port_open", return_value=True),
            patch("dashboard_hub.registry.pid_alive", return_value=False),
            patch("dashboard_hub.registry.port_serves_project", return_value=True),
        ):
            self.assertTrue(instance_healthy(instance))

    def test_port_serves_project_checks_listener_cwd(self) -> None:
        project_path = Path("/tmp/project")
        with (
            patch("dashboard_hub.registry.listening_pids", return_value={201}),
            patch(
                "dashboard_hub.registry.process_cwd",
                return_value=project_path.resolve(),
            ),
        ):
            self.assertTrue(port_serves_project(6420, project_path))


class RegistryConcurrencyTests(unittest.TestCase):
    def test_register_survives_concurrent_prune(self) -> None:
        import tempfile
        import threading
        from pathlib import Path

        from dashboard_hub.registry import (
            REGISTRY_LOCK_PATH,
            REGISTRY_PATH,
            RunningInstance,
            prune_registry,
            register_instance,
            utc_now,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir)
            registry_path = state_dir / "instances.json"
            lock_path = state_dir / ".instances.lock"
            wealth = RunningInstance(
                id="wealth",
                name="Wealth",
                path="/tmp/wealth",
                url="http://127.0.0.1:59901/",
                port=59901,
                pid=1,
                started_at=utc_now(),
            )
            mobile = RunningInstance(
                id="mobile",
                name="Mobile",
                path="/tmp/mobile",
                url="http://127.0.0.1:59902/",
                port=59902,
                pid=2,
                started_at=utc_now(),
            )

            with (
                patch("dashboard_hub.registry.REGISTRY_PATH", registry_path),
                patch("dashboard_hub.registry.REGISTRY_LOCK_PATH", lock_path),
                patch("dashboard_hub.registry.STATE_DIR", state_dir),
                patch("dashboard_hub.registry.instance_healthy", return_value=True),
            ):
                register_instance(wealth)
                barrier = threading.Barrier(2)

                def register_mobile() -> None:
                    barrier.wait()
                    register_instance(mobile)

                def refresh_many() -> None:
                    barrier.wait()
                    for _ in range(50):
                        prune_registry()

                threads = [
                    threading.Thread(target=register_mobile),
                    threading.Thread(target=refresh_many),
                ]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()

                saved_ids = {
                    item["id"]
                    for item in __import__("json").loads(registry_path.read_text(encoding="utf-8"))
                }
                self.assertEqual(saved_ids, {"wealth", "mobile"})


if __name__ == "__main__":
    unittest.main()
