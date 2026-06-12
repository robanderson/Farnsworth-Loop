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


def _parse_dispatch(entry, label):
    """Return (command, model) for a worker/reviewer entry.

    Exactly one of ``command`` (subprocess dispatch, e.g. ``claude -p`` or
    any non-Anthropic CLI) or ``model`` (delegate dispatch: the host
    session spawns a subagent on that Anthropic model, which bills to the
    subscription rather than API credit) must be present.
    """
    command = entry.get("command")
    model = entry.get("model")
    if (command is None) == (model is None):
        raise ConfigError(
            "{0} must have exactly one of 'command' (subprocess dispatch) "
            "or 'model' (delegate dispatch)".format(label)
        )
    if command is not None:
        if not isinstance(command, list) or not command:
            raise ConfigError(
                "{0} command must be a non-empty list".format(label)
            )
        if not all(isinstance(arg, str) for arg in command):
            raise ConfigError(
                "{0} command entries must be strings".format(label)
            )
        return list(command), None
    if not isinstance(model, str) or not model.strip():
        raise ConfigError(
            "{0} model must be a non-empty string".format(label)
        )
    return None, model.strip()


class Config:
    """Parsed run configuration."""

    def __init__(self, workers, reviewer, gate):
        self.workers = workers  # list of {"id": str, "command": list|None, "model": str|None}
        self.reviewer = reviewer  # {"command": list|None, "model": str|None} or None
        self.gate = gate

    @property
    def mode(self):
        """'delegate' when dispatch is via host-session subagents, else 'subprocess'.

        Mixed fleets are rejected at parse time, so the first worker decides.
        """
        return "delegate" if self.workers[0]["model"] else "subprocess"

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
                if not isinstance(worker_id, str) or not worker_id:
                    raise ConfigError("worker id must be a non-empty string")
                command, model = _parse_dispatch(
                    entry, "worker '{0}'".format(worker_id)
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
                        "command": command,
                        "model": model,
                        "timeout": _parse_timeout(
                            entry, "worker '{0}'".format(worker_id)
                        ),
                        "focus": _parse_focus(
                            entry, "worker '{0}'".format(worker_id)
                        ),
                    }
                )
            modes = {w["model"] is not None for w in workers}
            if len(modes) > 1:
                raise ConfigError(
                    "workers must all use the same dispatch mode: either every "
                    "entry has 'command' (subprocess) or every entry has "
                    "'model' (delegate)"
                )
        elif legacy_worker is not None:
            if not isinstance(legacy_worker, dict):
                raise ConfigError("legacy worker must be an object")
            command, model = _parse_dispatch(legacy_worker, "worker")
            workers = [
                {
                    "id": "w1",
                    "command": command,
                    "model": model,
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
            command, model = _parse_dispatch(reviewer_obj, "reviewer")
            reviewer = {
                "command": command,
                "model": model,
                "timeout": _parse_timeout(reviewer_obj, "reviewer"),
            }
            if (model is not None) != (workers[0]["model"] is not None):
                raise ConfigError(
                    "reviewer dispatch mode must match the workers' mode "
                    "(subprocess 'command' vs delegate 'model')"
                )

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
