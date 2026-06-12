"""Content-based field divergence measurement (Milestone M4).

Four recorded runs confirmed the same thing: blind same-family workers
produce IDENTICAL file footprints even under deliberate focus
diversification, so any footprint-based divergence metric reads zero and
the two-round trigger (PRD Section 2.2) can never fire on a well-briefed
task. The metric must read CONTENT.

This module scores a round's labeled candidate diffs by mean pairwise
Jaccard distance over the token sets of their changed lines: 0.0 means
every candidate changed the same tokens, 1.0 means no two candidates share
a changed token. The score is RECORDED in every run.json so a trigger
threshold can be calibrated against accumulated rounds before anything is
wired to it; nothing acts on the number yet.
"""

from __future__ import annotations

import itertools
import re

METRIC = "token-jaccard"


def _changed_line_tokens(diff_text):
    """Return the set of word tokens on the diff's added/removed lines."""
    tokens = set()
    for line in diff_text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+") or line.startswith("-"):
            tokens.update(re.findall(r"\w+", line[1:]))
    return tokens


def divergence(diff_texts):
    """Score a field of candidate diffs; None when fewer than two.

    Returns ``{"metric": "token-jaccard", "score": float, "candidates": n}``
    where score is the mean pairwise Jaccard distance (0.0 identical,
    1.0 disjoint) across the candidates' changed-line token sets.
    """
    if len(diff_texts) < 2:
        return None
    token_sets = [_changed_line_tokens(text) for text in diff_texts]
    distances = []
    for left, right in itertools.combinations(token_sets, 2):
        union = left | right
        if not union:
            distances.append(0.0)
        else:
            distances.append(1.0 - len(left & right) / len(union))
    return {
        "metric": METRIC,
        "score": round(sum(distances) / len(distances), 4),
        "candidates": len(diff_texts),
    }
