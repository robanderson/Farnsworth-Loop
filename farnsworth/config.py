"""Run configuration for the Farnsworth Loop.

The config makes the worker command and the mechanical gate fully
configurable. This is a hard requirement: the worker command is swappable so
that tests can substitute a fake worker and never invoke the real ``claude``
binary.
"""

from __future__ import annotations

import json
import os

DEFAULT_CONFIG_NAME = "farnsworth.json"

# Used when no config file is found. Mirrors the schema in the task brief.
DEFAULT_CONFIG = {
    "workers": [
        {
            "id": "w1",
            "command": [
                "claude",
                "-p",
                "{prompt}",
                "--bare",
                "--model",
                "claude-haiku-4-5",
                "--permission-mode",
                "acceptEdits",
                "--output-format",
                "json",
            ],
        }
    ],
    "gate": [
        {"name": "tests", "command": ["python3", "-m", "unittest", "discover"]}
    ],
}


class ConfigError(RuntimeError):
    """Raised when the config file is missing required structure."""


def _parse_timeout(obj, label):
    """Return a validated optional ``timeout_seconds`` from ``obj``.

    None when absent; otherwise a positive number. Anything else is a
    ConfigError.
    """
    timeout = obj.get("timeout_seconds")
    if timeout is None:
        return None
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise ConfigError(
            "{0} timeout_seconds must be a number".format(label)
        )
    if timeout <= 0:
        raise ConfigError(
            "{0} timeout_seconds must be positive".format(label)
        )
    return timeout


def _parse_focus(obj, label):
    """Return a validated optional ``focus`` directive from ``obj``.

    None when absent; otherwise a non-empty string (e.g. "Focus on runtime
    speed"). Anything else is a ConfigError.
    """
    focus = obj.get("focus")
    if focus is None:
        return None
    if not isinstance(focus, str) or not focus.strip():
        raise ConfigError(
            "{0} focus must be a non-empty string".format(label)
        )
    return focus.strip()


class Config:
    """Parsed run configuration."""

    def __init__(self, workers, reviewer, gate):
        self.workers = workers  # list of {"id": str, "command": list}
        self.reviewer = reviewer  # {"command": list} or None
        self.gate = gate

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ConfigError("config root must be a JSON object")

        # Handle both new "workers" (list) and legacy "worker" (single).
        workers_list = data.get("workers")
        legacy_worker = data.get("worker")

        if workers_list is not None and legacy_worker is not None:
            raise ConfigError("config cannot have both 'workers' and 'worker'")

        if workers_list is not None:
            if not isinstance(workers_list, list):
                raise ConfigError("workers must be a list")
            if not workers_list:
                raise ConfigError("workers list must not be empty")
            workers = []
            seen_ids = set()
            for entry in workers_list:
                if not isinstance(entry, dict):
                    raise ConfigError("each worker entry must be an object")
                worker_id = entry.get("id")
                command = entry.get("command")
                if not isinstance(worker_id, str) or not worker_id:
                    raise ConfigError("worker id must be a non-empty string")
                if not isinstance(command, list) or not command:
                    raise ConfigError(
                        "worker '{0}' command must be a non-empty list".format(
                            worker_id
                        )
                    )
                if not all(isinstance(arg, str) for arg in command):
                    raise ConfigError(
                        "worker '{0}' command entries must be strings".format(
                            worker_id
                        )
                    )
                # Validate filesystem-safe id (alphanumeric and underscore).
                if not all(c.isalnum() or c == "_" for c in worker_id):
                    raise ConfigError(
                        "worker id '{0}' must be filesystem-safe (alphanumeric or underscore)".format(
                            worker_id
                        )
                    )
                if worker_id in seen_ids:
                    raise ConfigError("duplicate worker id: {0}".format(worker_id))
                seen_ids.add(worker_id)
                workers.append(
                    {
                        "id": worker_id,
                        "command": list(command),
                        "timeout": _parse_timeout(
                            entry, "worker '{0}'".format(worker_id)
                        ),
                        "focus": _parse_focus(
                            entry, "worker '{0}'".format(worker_id)
                        ),
                    }
                )
        elif legacy_worker is not None:
            if not isinstance(legacy_worker, dict):
                raise ConfigError("legacy worker must be an object")
            command = legacy_worker.get("command")
            if not isinstance(command, list) or not command:
                raise ConfigError("worker.command must be a non-empty list")
            if not all(isinstance(arg, str) for arg in command):
                raise ConfigError("worker.command entries must be strings")
            workers = [
                {
                    "id": "w1",
                    "command": list(command),
                    "timeout": _parse_timeout(legacy_worker, "worker"),
                    "focus": _parse_focus(legacy_worker, "worker"),
                }
            ]
        else:
            raise ConfigError("config must contain 'workers' or 'worker'")

        # Parse reviewer (optional, required if >0 workers pass gate).
        reviewer_obj = data.get("reviewer")
        reviewer = None
        if reviewer_obj is not None:
            if not isinstance(reviewer_obj, dict):
                raise ConfigError("reviewer must be an object")
            reviewer_command = reviewer_obj.get("command")
            if not isinstance(reviewer_command, list) or not reviewer_command:
                raise ConfigError("reviewer.command must be a non-empty list")
            if not all(isinstance(arg, str) for arg in reviewer_command):
                raise ConfigError("reviewer.command entries must be strings")
            reviewer = {
                "command": list(reviewer_command),
                "timeout": _parse_timeout(reviewer_obj, "reviewer"),
            }

        # Parse gate.
        gate = data.get("gate")
        if gate is None:
            gate = []
        if not isinstance(gate, list):
            raise ConfigError("gate must be a list")
        normalized_gate = []
        for entry in gate:
            if not isinstance(entry, dict):
                raise ConfigError("each gate entry must be an object")
            name = entry.get("name")
            gate_command = entry.get("command")
            if not isinstance(name, str) or not name:
                raise ConfigError("gate entry needs a non-empty 'name'")
            if not isinstance(gate_command, list) or not gate_command:
                raise ConfigError(
                    "gate entry '{0}' needs a non-empty command list".format(
                        name
                    )
                )
            if not all(isinstance(arg, str) for arg in gate_command):
                raise ConfigError(
                    "gate command for '{0}' must be strings".format(name)
                )
            normalized_gate.append({"name": name, "command": list(gate_command)})

        return cls(workers, reviewer, normalized_gate)

    @classmethod
    def load(cls, path):
        """Load config from ``path``; fall back to DEFAULT_CONFIG if absent.

        If ``path`` is provided explicitly but does not exist, that is an
        error. If ``path`` is the default location and is absent, the built-in
        DEFAULT_CONFIG is used.
        """
        if path is None or not os.path.exists(path):
            return cls.from_dict(DEFAULT_CONFIG)
        with open(path, "r", encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as exc:
                raise ConfigError(
                    "config {0} is not valid JSON: {1}".format(path, exc)
                )
        return cls.from_dict(data)
