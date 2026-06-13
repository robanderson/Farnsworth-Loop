"""Improvement rounds: the bounded, self-evaluating Ralph (PRD Section 2.7).

When both halves of done pass and improvement rounds remain, the loop
does not exit. The improver agent probes the finished deliverable as a
user and AMENDS the goal — append-only: every prior check stays, the
contract only ratchets, no round can hand back less than it received.
New criteria route by enforceability: mechanizable -> ``goal.done``
checks; semantic -> the goal brief, where attestation reads them.

This module is the trust-layer half: it counts rounds from committed
artifacts (never hidden state), writes the improvement briefing (a
protocol traveling inside an orchestrator prompt is a protocol that
drifts), and mechanically validates a proposal before installing it —
the additive-only rule is enforced here, not hoped for in a prompt.

Artifacts per round N (the changelog that banks the round):

    .farnsworth/improvement-00N/proposal.md        what, why, probe evidence
    .farnsworth/improvement-00N/done-checks.json   mechanizable criteria
    <goal brief>  gains an appended "## Improvement round N" section
"""

from __future__ import annotations

import json
import os
import re

from . import gitutil
from .config import ConfigError, _parse_check_list

ROUND_DIR_RE = re.compile(r"^improvement-(\d{3})$")
BRIEFING_NAME = "improvement-briefing.md"
NONE_MARKER = "improvement: none"


class ImproveError(RuntimeError):
    """Raised when a proposal violates its artifact contract (exit 1)."""


class ImprovePreconditionError(RuntimeError):
    """Raised when ``improve`` is invoked out of sequence (exit 2)."""


def round_dir_name(round_number):
    """``1 -> improvement-001`` (filesystem-sortable, like task ids)."""
    return "improvement-{0:03d}".format(round_number)


def completed_rounds(repo_root):
    """Count completed rounds from committed artifacts, never memory.

    A round is complete when its ``.farnsworth/improvement-NNN/`` dir
    holds a non-empty ``proposal.md`` (an applied amendment or a
    recorded decline both count: each consumed the round).
    """
    base = os.path.join(repo_root, ".farnsworth")
    if not os.path.isdir(base):
        return 0
    count = 0
    for name in os.listdir(base):
        if not ROUND_DIR_RE.match(name):
            continue
        proposal = os.path.join(base, name, "proposal.md")
        if os.path.exists(proposal) and os.path.getsize(proposal) > 0:
            count += 1
    return count


def improvement_status(goal, repo_root, rounds_override=None):
    """``{"configured": N, "completed": M, "remaining": max(0, N-M)}``.

    ``rounds_override`` is the run-scoped count a conductor confirmed at
    ignition (like the fleet, the config value is a default, not a
    fixture); the override travels in the command line, so the choice
    is visible in history.
    """
    configured = goal.get("improvement_rounds", 0)
    if rounds_override is not None:
        configured = rounds_override
    completed = completed_rounds(repo_root)
    return {
        "configured": configured,
        "completed": completed,
        "remaining": max(0, configured - completed),
    }


def build_improvement_briefing(goal, round_number, configured):
    """The improver protocol for round ``round_number`` of ``configured``."""
    brief = goal.get("brief")
    brief_line = (
        "Goal brief: {0}".format(brief)
        if brief
        else "Goal brief: (none configured)"
    )
    proposal_dir = ".farnsworth/{0}".format(round_dir_name(round_number))
    lines = [
        "# Improvement Round Briefing (round {0} of {1})".format(
            round_number, configured
        ),
        "",
        "Both halves of done pass: the goal as written is met. You are the",
        "IMPROVEMENT AGENT (PRD Section 2.7). Probe the finished deliverable",
        "AS A USER, ask and answer \"how can this be better?\", and AMEND the",
        "goal with your answer -- or attest that nothing is left worth a",
        "round. The loop then cycles against the raised bar.",
        "",
        brief_line,
        "",
        "## Protocol",
        "",
        "1. Read the goal brief (including every prior \"## Improvement",
        "   round\" section), .farnsworth/orchestrator-log.md, and",
        "   .code-tips.md. Prior rounds live in",
        "   .farnsworth/improvement-*/ -- do not repeat them.",
        "2. Probe the deliverable EMPIRICALLY as a user: run it, exercise",
        "   it, feed it hostile input. Never propose from reading alone.",
        "3. Propose a SMALL, coherent set of improvements (2-5) that are",
        "   each attestable or gateable, within the spirit of the original",
        "   objective -- quality, UX, robustness, performance, features the",
        "   goal implies. Not speculative scope explosion.",
        "4. Write {0}/proposal.md: what, why, and the".format(proposal_dir),
        "   probe evidence behind each improvement.",
        "5. Route each new criterion by enforceability:",
        "   - mechanizable -> {0}/done-checks.json,".format(proposal_dir),
        '     a JSON list of {"name": ..., "command": [...]} entries',
        "     (same schema as goal.done; omit the file if none);",
        "   - semantic -> the appended goal-brief section, where the",
        "     attestor reads it.",
        "6. Append one \"## Improvement round {0}\" section to the".format(
            round_number
        ),
        "   goal brief: the new criteria, with date and evidence pointer.",
        "   APPEND-ONLY: never weaken, reword, or remove anything already",
        "   in the brief -- the contract only ratchets, and the trust layer",
        "   rejects a proposal that hands back less than it received.",
        "7. If nothing is left worth a round, write",
        "   {0}/proposal.md beginning with the exact".format(proposal_dir),
        "   line \"{0}\" followed by your reasoning -- skipping".format(
            NONE_MARKER
        ),
        "   carries the burden of proof, and the loop exits DONE with",
        "   rounds unspent. Do not amend the brief in that case.",
        "",
        "You propose; you never fix. Do not modify project code -- every",
        "improvement enters the codebase through a tournament task like any",
        "other change. The conductor validates and installs your proposal",
        "with `farnsworth improve --apply {0}`.".format(proposal_dir),
        "",
    ]
    return "\n".join(lines)


def prepare(config, repo_root, rounds_override=None):
    """The bare ``farnsworth improve``: precondition probe + briefing.

    Preconditions (each a sequencing error when unmet -- the conductor
    called improve out of order): a goal with a brief is configured,
    the latest recorded done probe passed, and ``attestation.json``
    holds ``goal_met: true``. Rounds remaining is NOT a precondition:
    it is the payload's answer (``remaining == 0`` is the honest "stop
    improving" signal, reported via exit code 1 by the CLI).

    Writes ``.farnsworth/improvement-briefing.md`` and returns the
    payload for the conductor.
    """
    goal = config.goal
    if goal is None:
        raise ImprovePreconditionError(
            "no goal configured -- improvement rounds ratchet a goal "
            "contract; add a 'goal' entry first (PRD Section 2.4)"
        )
    if not goal.get("brief"):
        raise ImprovePreconditionError(
            "goal has no brief file -- improvement rounds amend the goal "
            "brief append-only; declare goal.brief (e.g. GOAL.md)"
        )
    brief_path = os.path.join(repo_root, goal["brief"])
    if not os.path.exists(brief_path):
        raise ImprovePreconditionError(
            "goal brief not found: {0}".format(goal["brief"])
        )

    done_record = os.path.join(repo_root, ".farnsworth", "done-checks.json")
    try:
        with open(done_record, "r", encoding="utf-8") as fh:
            record = json.load(fh)
    except (FileNotFoundError, ValueError):
        record = None
    if not record or not record.get("passed"):
        raise ImprovePreconditionError(
            "the mechanical half is not green: run `farnsworth done` and "
            "reach a passing probe before an improvement round"
        )

    attestation_path = os.path.join(
        repo_root, ".farnsworth", "attestation.json"
    )
    try:
        with open(attestation_path, "r", encoding="utf-8") as fh:
            attestation = json.load(fh)
    except (FileNotFoundError, ValueError):
        attestation = None
    if not attestation or attestation.get("goal_met") is not True:
        raise ImprovePreconditionError(
            "no attestation with goal_met true on record: the semantic "
            "half must pass before the goal may ratchet (PRD Section 2.7)"
        )

    status = improvement_status(goal, repo_root, rounds_override)
    round_number = status["completed"] + 1
    payload = {
        "rounds": status,
        "round": round_number if status["remaining"] > 0 else None,
        "proposal_dir": (
            ".farnsworth/{0}".format(round_dir_name(round_number))
            if status["remaining"] > 0
            else None
        ),
        "briefing": None,
    }
    if status["remaining"] == 0:
        return payload

    farnsworth_dir = os.path.join(repo_root, ".farnsworth")
    os.makedirs(farnsworth_dir, exist_ok=True)
    briefing_path = os.path.join(farnsworth_dir, BRIEFING_NAME)
    with open(briefing_path, "w", encoding="utf-8") as fh:
        fh.write(
            build_improvement_briefing(
                goal, round_number, status["configured"]
            )
        )
    payload["briefing"] = os.path.relpath(briefing_path, repo_root)
    return payload


def _committed_text(rel_path, repo_root):
    """The HEAD version of ``rel_path``, or None when not yet tracked."""
    try:
        proc = gitutil.run_git(
            ["show", "HEAD:{0}".format(rel_path)], repo_root
        )
    except gitutil.GitError:
        return None
    return proc.stdout


def is_decline(proposal_text):
    """True when the proposal's first non-blank line is the none marker."""
    for line in proposal_text.splitlines():
        if line.strip():
            return line.strip() == NONE_MARKER
    return False


def apply_proposal(proposal_dir, config, config_path, repo_root):
    """``farnsworth improve --apply``: validate, then install.

    Mechanical validation of the improver's artifact contract; any
    violation raises ImproveError (exit 1 -- re-spawn the improver,
    never hand-patch a proposal):

    - the dir matches ``improvement-NNN`` and holds a non-empty
      proposal.md that is not a decline (a decline installs nothing);
    - the goal brief was amended ADDITIVELY: the HEAD version is a
      verbatim prefix of the working version, and something was added;
    - done-checks.json (when present) parses through the same
      validator as ``goal.done`` and collides with no existing check
      name.

    On success the new checks are merged into the config file's
    ``goal.done`` and the result summary is returned. The conductor
    commits the round's artifacts.
    """
    abs_dir = (
        proposal_dir
        if os.path.isabs(proposal_dir)
        else os.path.join(repo_root, proposal_dir)
    )
    name = os.path.basename(os.path.normpath(abs_dir))
    match = ROUND_DIR_RE.match(name)
    if not match:
        raise ImproveError(
            "proposal dir must be named improvement-NNN, got: {0}".format(
                name
            )
        )
    round_number = int(match.group(1))

    proposal_path = os.path.join(abs_dir, "proposal.md")
    if not os.path.exists(proposal_path) or os.path.getsize(proposal_path) == 0:
        raise ImproveError(
            "proposal.md is missing or empty in {0}".format(proposal_dir)
        )
    with open(proposal_path, "r", encoding="utf-8") as fh:
        proposal_text = fh.read()
    if is_decline(proposal_text):
        raise ImproveError(
            "proposal declines the round ('{0}'): nothing to apply -- the "
            "loop exits DONE with rounds unspent".format(NONE_MARKER)
        )

    goal = config.goal
    if goal is None or not goal.get("brief"):
        raise ImprovePreconditionError(
            "no goal brief configured; nothing to amend"
        )
    brief_rel = goal["brief"]
    brief_abs = os.path.join(repo_root, brief_rel)
    if not os.path.exists(brief_abs):
        raise ImproveError("goal brief not found: {0}".format(brief_rel))
    with open(brief_abs, "r", encoding="utf-8") as fh:
        amended = fh.read()
    committed = _committed_text(brief_rel, repo_root)
    if committed is not None:
        base_text = committed.rstrip("\n")
        if not amended.startswith(base_text):
            raise ImproveError(
                "goal brief amendment is not append-only: the committed "
                "{0} must survive verbatim as a prefix -- the contract "
                "only ratchets; no round hands back less than it "
                "received".format(brief_rel)
            )
        if len(amended.rstrip("\n")) <= len(base_text):
            raise ImproveError(
                "goal brief is unchanged: an applied round must append "
                "its '## Improvement round {0}' section to {1}".format(
                    round_number, brief_rel
                )
            )

    checks_path = os.path.join(abs_dir, "done-checks.json")
    new_checks = []
    if os.path.exists(checks_path):
        try:
            with open(checks_path, "r", encoding="utf-8") as fh:
                raw_checks = json.load(fh)
        except ValueError as exc:
            raise ImproveError(
                "done-checks.json is not valid JSON: {0}".format(exc)
            )
        try:
            new_checks = _parse_check_list(
                raw_checks, "improvement done-checks"
            )
        except ConfigError as exc:
            raise ImproveError(str(exc))
        existing = {check["name"] for check in goal["done"]}
        for check in new_checks:
            if check["name"] in existing:
                raise ImproveError(
                    "proposed check '{0}' collides with an existing done "
                    "check; prior checks are immutable -- pick a new "
                    "name".format(check["name"])
                )

    if new_checks:
        _install_checks(new_checks, config_path)

    return {
        "round": round_number,
        "goal_brief": brief_rel,
        "added_checks": [check["name"] for check in new_checks],
        "rounds": improvement_status(goal, repo_root),
    }


def _install_checks(new_checks, config_path):
    """Append validated checks to the config file's ``goal.done``.

    Operates on the raw JSON so every key the project put in the config
    survives untouched; only ``goal.done`` grows. The config file is a
    contract file -- this append, validated upstream, is the one
    sanctioned mechanical edit.
    """
    with open(config_path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    done = raw.setdefault("goal", {}).setdefault("done", [])
    for check in new_checks:
        entry = {"name": check["name"], "command": check["command"]}
        if check.get("timeout") is not None:
            entry["timeout_seconds"] = check["timeout"]
        done.append(entry)
    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump(raw, fh, indent=2)
        fh.write("\n")
