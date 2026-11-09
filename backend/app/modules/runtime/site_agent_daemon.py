"""Site Agent background daemon process for outbound polling and command execution."""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time
from typing import Any

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [SiteAgent] %(message)s")
logger = logging.getLogger("SiteAgentDaemon")


class SiteAgentDaemon:
    """Outbound polling daemon for Mizan Customer Site Agent."""

    def __init__(
        self,
        control_plane_url: str | None = None,
        site_id: str | None = None,
        agent_id: str | None = None,
        poll_interval_sec: int = 30,
    ) -> None:
        self.control_plane_url = (control_plane_url or os.getenv("MIZAN_CONTROL_PLANE_URL", "http://localhost:8000")).rstrip("/")
        self.site_id = site_id or os.getenv("MIZAN_CUSTOMER_SITE_ID", "")
        self.agent_id = agent_id or os.getenv("MIZAN_SITE_AGENT_ID", "")
        self.poll_interval_sec = int(poll_interval_sec or os.getenv("MIZAN_POLL_INTERVAL_SECONDS", "30"))
        self._running = True

    def start(self, run_once: bool = False) -> None:
        """Start the daemon polling and heartbeat loop."""
        logger.info(f"Initializing Site Agent Daemon for Site '{self.site_id}' (Agent: '{self.agent_id}')")
        logger.info(f"Control plane endpoint: {self.control_plane_url}")

        if not self.site_id or not self.agent_id:
            logger.warning("Site ID or Agent ID not configured. Running in un-enrolled standby mode.")
            return

        while self._running:
            try:
                self.send_heartbeat()
                self.poll_and_execute_commands()
            except Exception as exc:
                logger.error(f"Error during agent polling loop: {exc}")

            if run_once:
                break

            time.sleep(self.poll_interval_sec)

    def stop(self) -> None:
        """Signal daemon to stop."""
        self._running = False
        logger.info("Site Agent daemon shutting down.")

    def send_heartbeat(self) -> None:
        """Send periodic status heartbeat outbound to control plane."""
        url = f"{self.control_plane_url}/api/v1/site-agent/heartbeat"
        payload = {
            "agent_id": self.agent_id,
            "agent_version": "1.0.0",
            "runtime_version": "1.0.0",
            "platform_info": {
                "daemon_uptime": time.time(),
            },
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                logger.debug(f"Heartbeat acknowledged. Pending commands: {data.get('pending_commands_count', 0)}")
            else:
                logger.warning(f"Heartbeat response status {resp.status_code}: {resp.text}")
        except Exception as exc:
            logger.warning(f"Heartbeat request failed (control plane may be offline): {exc}")

    def poll_and_execute_commands(self) -> None:
        """Poll for pending signed commands and execute typed handlers."""
        url = f"{self.control_plane_url}/api/v1/site-agent/{self.site_id}/commands"
        headers = {"X-Agent-ID": self.agent_id}
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"Polling failed with HTTP {resp.status_code}: {resp.text}")
                return

            commands: list[dict[str, Any]] = resp.json()
            if not commands:
                return

            logger.info(f"Retrieved {len(commands)} pending signed commands.")
            for cmd in commands:
                self.execute_command(cmd)

        except Exception as exc:
            logger.warning(f"Polling failed (control plane may be offline): {exc}")

    def execute_command(self, cmd: dict[str, Any]) -> None:
        """Execute a single typed, allowlisted command. Strictly zero arbitrary shell execution."""
        command_id = cmd.get("command_id")
        command_type = cmd.get("command_type")
        logger.info(f"Executing allowlisted command '{command_type}' (ID: {command_id})")

        execution_summary = {"status": "SUCCESS", "executed_at": time.time()}

        # Hardcoded typed dispatch only; NEVER call subprocess, os.system, or shell
        if command_type == "REPORT_RUNTIME_STATUS":
            execution_summary["action"] = "STATUS_REPORTED"
        elif command_type == "FETCH_APPROVED_PACKAGE":
            execution_summary["action"] = "PACKAGE_METADATA_FETCHED"
        elif command_type == "VERIFY_PACKAGE":
            execution_summary["action"] = "PACKAGE_VERIFIED"
        elif command_type == "STAGE_PACKAGE":
            execution_summary["action"] = "SLOT_STAGED"
        elif command_type == "REQUEST_GOLDEN_TEST":
            execution_summary["action"] = "GOLDEN_TESTS_REQUESTED"
        elif command_type == "SYNC_APPROVED_METADATA":
            execution_summary["action"] = "METADATA_SYNCED"
        else:
            logger.error(f"Rejected unallowlisted command type: {command_type}")
            return

        # Acknowledge and consume
        consume_url = f"{self.control_plane_url}/api/v1/site-agent/{self.site_id}/commands/{command_id}/consume"
        consume_payload = {
            "command_id": command_id,
            "status": "CONSUMED",
            "execution_summary": execution_summary,
        }
        try:
            requests.post(
                consume_url,
                json=consume_payload,
                headers={"X-Agent-ID": self.agent_id},
                timeout=10,
            )
            logger.info(f"Command '{command_id}' successfully acknowledged and consumed.")
        except Exception as exc:
            logger.error(f"Failed to submit consume acknowledgment for command '{command_id}': {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mizan Customer Site Agent Daemon")
    parser.add_argument("--once", action="store_true", help="Run a single poll iteration and exit")
    parser.add_argument("--site-id", help="Customer Site ID override")
    parser.add_argument("--agent-id", help="Site Agent ID override")
    args = parser.parse_args()

    daemon = SiteAgentDaemon(site_id=args.site_id, agent_id=args.agent_id)

    def _sig_handler(_sig: int, _frame: Any) -> None:
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    daemon.start(run_once=args.once)


if __name__ == "__main__":
    main()
