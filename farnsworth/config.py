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
    "worker": {
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
        ]
    },
    "gate": [
        {"name": "tests", "command": ["python3", "-m", "unittest", "discover"]}
    ],
}


class ConfigError(RuntimeError):
    """Raised when the config file is missing required structure."""


class Config:
    """Parsed run configuration."""

    def __init__(self, worker_command, gate):
        self.worker_command = worker_command
        self.gate = gate

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ConfigError("config root must be a JSON object")

        worker = data.get("worker")
        if not isinstance(worker, dict):
            raise ConfigError("config must contain a 'worker' object")
        command = worker.get("command")
        if not isinstance(command, list) or not command:
            raise ConfigError("worker.command must be a non-empty list")
        if not all(isinstance(arg, str) for arg in command):
            raise ConfigError("worker.command entries must be strings")

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

        return cls(list(command), normalized_gate)

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
