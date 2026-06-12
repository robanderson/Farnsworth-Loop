"""Run summary rendering: a short display table explaining what happened.

``summary_table`` turns a run log (the ``run.json`` contract) into a small
GitHub-flavored markdown table plus the verdict, readable both in a terminal
and when committed next to the run log. Output is ASCII-only.

When the run log's review block carries a ``progression`` note (the
reviewer's post-verdict explanation of how the merged code advances the
previously adopted baseline), it is rendered after the reasoning, so the
summary answers both questions a reader has: who won the round, and how
the project moved.
"""

from __future__ import annotations


def _gate_cell(worker):
    """One-word gate status, with the first failing autopsy when it failed."""
    gate = worker["gate"]
    if gate["passed"]:
        return "PASS"
    for result in gate["results"]:
        if result["exit_code"] != 0:
            return "FAIL ({0})".format(result["autopsy"])
    return "FAIL"


def summary_table(run_log):
    """Render the short what-happened table for one task run."""
    review = run_log.get("review")
    verdict = review.get("verdict") if review else None
    if verdict is None:
        # Legacy manual-mode logs keep the verdict at the top level.
        verdict = run_log.get("verdict")
    adopted = None
    if verdict and verdict.get("outcome") == "adopt":
        adopted = verdict.get("candidate")

    lines = []
    lines.append("# Run summary -- {0}".format(run_log["task_id"]))
    lines.append("")
    lines.append(
        "Base commit `{0}`, {1} -> {2}.".format(
            run_log["base_commit"][:12],
            run_log["started_at"],
            run_log["finished_at"],
        )
    )
    lines.append("")
    lines.append("| Worker | Focus | Exit | Gate | Candidate | Result |")
    lines.append("|---|---|---:|---|---|---|")
    for worker in run_log["workers"]:
        label = worker.get("candidate_label") or "-"
        result = "ADOPTED" if adopted is not None and label == adopted else ""
        lines.append(
            "| {0} | {1} | {2} | {3} | {4} | {5} |".format(
                worker["id"],
                worker.get("focus") or "-",
                worker["exit_code"],
                _gate_cell(worker),
                label,
                result,
            )
        )
    lines.append("")

    if review is None and verdict is None:
        lines.append("No candidates passed the gate; no review was run.")
    elif verdict is None:
        lines.append("Review ran but recorded no verdict (legacy or partial log).")
    else:
        candidate = verdict.get("candidate")
        suffix = " candidate {0}".format(candidate) if candidate else ""
        lines.append("**Verdict:** {0}{1}".format(verdict["outcome"], suffix))
        lines.append("")
        reasoning = verdict.get("reasoning") or verdict.get("rationale") or ""
        lines.append("**Reasoning:** {0}".format(reasoning))
        # Manual-mode logs record the progression note on the review block;
        # CLI runs carry it inside the verdict artifact itself.
        progression = review.get("progression") if review else None
        if not progression:
            progression = verdict.get("progression")
        if progression:
            lines.append("")
            lines.append("**Progression:** {0}".format(progression))
    lines.append("")
    return "\n".join(lines)
