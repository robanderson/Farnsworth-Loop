# Goal Attestation Briefing

The mechanical done checks pass. Mechanics are necessary, not
sufficient: you are the SEMANTIC half of the termination contract
(PRD Section 2.4). Attest -- or refuse to attest -- that the merged
state meets the goal brief's acceptance criteria. Exit DONE requires
both halves.

Goal brief: GOAL.md

## Protocol

1. Read the goal brief and enumerate its acceptance criteria.
2. Verify each criterion EMPIRICALLY against the merged state (run
   the code, probe the behavior); never attest from reading alone.
3. Write the full attestation to .farnsworth/attestation.md:
   per-criterion evidence, and any residual gaps.
4. Write .farnsworth/attestation.json LAST, with schema:

   {"goal_met": true | false, "reasoning": "..."}

goal_met true means the loop exits DONE. goal_met false means the
loop keeps cycling, and your reasoning must name the gap the next
task brief should close.
