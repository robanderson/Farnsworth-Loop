// The Farnsworth LOOP as a Claude Code dynamic workflow — the OUTER
// cycle that makes it a loop at all: a -> b -> c -> a.
//
//   probe the goal -> derive the smallest next task -> run the
//   two-round tournament (nested farnsworth-task workflow) -> merge ->
//   inspect against the goal -> GO AGAIN, with the attested gap as the
//   next instruction — and when both halves pass with improvement
//   rounds remaining, the improver ratchets the goal (append-only,
//   PRD 2.7) and the loop goes again against the raised bar — until
//   DONE, ESCALATED, STOPPED, or STALLED (PRD Section 2.4: exactly
//   four exits, every one recorded).
//
// Iteration count is EMERGENT: nothing here pre-authors a task list.
// Each pass derives one task — the smallest coherent slice of the goal
// gap that is independently gateable — and the next pass re-reads the
// goal against the newly merged state.
//
// Launch with args, e.g.:
//   { repo: '/abs/path/to/project', farnsworthPath: '/path/to/Farnsworth-Loop',
//     maxIterations: 8, improvementRounds: 1, fleet: [...],
//     config: 'farnsworth.json' }
// Requires a `goal` entry (done checks) in the fleet config — a loop
// without a termination contract either stops early or never.
// improvementRounds (PRD 2.7) is confirmed at ignition like the fleet;
// when omitted, the config's goal.improvement_rounds (default 0) rules.

export const meta = {
  name: 'farnsworth-loop',
  description:
    'The goal cycle: probe done -> derive the smallest next task -> ' +
    'nested farnsworth-task tournament -> merge -> attest -> improvement ' +
    'rounds ratchet the goal -> loop. Exits DONE / ESCALATED / STOPPED / ' +
    'STALLED, all recorded.',
  phases: [
    { title: 'Probe' },
    { title: 'Premise' },
    { title: 'Task' },
    { title: 'Attest' },
    { title: 'Improve' },
  ],
};

const repo = args.repo;
const pp = args.farnsworthPath ? `PYTHONPATH=${args.farnsworthPath} ` : '';
const cfg = args.config ? ` --config ${args.config}` : '';
const maxIterations = args.maxIterations || 8; // the STOPPED budget
// Run-scoped improvement budget: travels on the improve command line so
// the choice is visible in history; the trust layer counts completed
// rounds from committed artifacts, never from this script's memory.
const roundsFlag =
  args.improvementRounds === undefined
    ? ''
    : ` --rounds ${args.improvementRounds}`;

let stalls = 0; // consecutive iterations without done-check progress
let bestPassCount = -1;
let gap = null; // the attestor's named gap = the next instruction
let improvementsBanked = 0;

for (let i = 1; i <= maxIterations; i++) {
  // ---- PROBE: is the goal already met, mechanically? ----
  phase(`Probe ${i}`);
  const probe = await agent(
    `cd ${repo} && run \`${pp}python3 -m farnsworth done --json${cfg}\` ` +
      'and relay its JSON verbatim plus the exit code (0 mechanical ' +
      'done, 1 keep looping, 2 no goal configured — fatal).',
    {
      model: 'haiku',
      schema: {
        type: 'object',
        properties: {
          exit_code: { type: 'number' },
          passed: { type: 'boolean' },
          results: { type: 'array' },
          attestation_briefing: { type: ['string', 'null'] },
        },
        required: ['exit_code', 'passed', 'results'],
      },
    }
  );
  if (probe.exit_code === 2) {
    throw new Error(
      'no goal configured — a loop without a termination contract ' +
        'either stops early or never (PRD 2.4); add goal.done checks'
    );
  }

  // ---- ATTEST: mechanics are necessary, not sufficient ----
  if (probe.passed) {
    phase(`Attest ${i}`);
    const attestation = await agent(
      `You are the farnsworth-attestor. cd ${repo} and work there. Your ` +
        `briefing is ${repo}/${probe.attestation_briefing} — read it ` +
        'FIRST and follow it exactly: enumerate the goal brief\'s ' +
        'acceptance criteria, verify each EMPIRICALLY against the ' +
        'merged state (run the code; never attest from reading), write ' +
        '.farnsworth/attestation.md then .farnsworth/attestation.json ' +
        'LAST. You verify; you never fix. A refused attestation that ' +
        'names the gap is the loop working.',
      {
        agent: 'farnsworth-attestor',
        model: 'opus',
        schema: {
          type: 'object',
          properties: {
            goal_met: { type: 'boolean' },
            reasoning: { type: 'string' },
          },
          required: ['goal_met', 'reasoning'],
        },
      }
    );
    if (attestation.goal_met) {
      // ---- IMPROVE (PRD 2.7): goal met — rounds remaining? ----
      phase(`Improve ${i}`);
      const boundary = await agent(
        `cd ${repo} && run \`${pp}python3 -m farnsworth improve ` +
          `--json${roundsFlag}${cfg}\` and relay its JSON verbatim plus ` +
          'the exit code (3 = improvement round open, improver agent ' +
          'next; 1 = no rounds remaining, exit DONE; 2 = sequencing ' +
          'error — fatal).',
        {
          model: 'haiku',
          schema: {
            type: 'object',
            properties: {
              exit_code: { type: 'number' },
              round: { type: ['number', 'null'] },
              proposal_dir: { type: ['string', 'null'] },
              briefing: { type: ['string', 'null'] },
              rounds: { type: 'object' },
            },
            required: ['exit_code', 'rounds'],
          },
        }
      );
      if (boundary.exit_code === 2) {
        throw new Error(
          'improvement-round preconditions failed after a passing ' +
            'attestation — sequencing bug, inspect .farnsworth/'
        );
      }
      if (boundary.exit_code === 1) {
        return {
          exit: 'DONE',
          iterations: i,
          improvement_rounds: improvementsBanked,
          reasoning: attestation.reasoning,
        };
      }

      const improvement = await agent(
        `You are the farnsworth-improver. cd ${repo} and work there. ` +
          `Your briefing is ${repo}/${boundary.briefing} — read it FIRST ` +
          'and follow it exactly: probe the deliverable AS A USER (run ' +
          'it; never propose from reading alone), then either write ' +
          `${boundary.proposal_dir}/proposal.md + done-checks.json and ` +
          'append ONE "## Improvement round" section to the goal brief ' +
          '(APPEND-ONLY: never weaken or remove anything), or decline ' +
          `with a proposal.md starting "improvement: none" — skipping ` +
          'carries the burden of proof. You propose; you never fix code.',
        {
          agent: 'farnsworth-improver',
          model: 'opus',
          schema: {
            type: 'object',
            properties: {
              improvement: { type: 'string', enum: ['proposed', 'none'] },
              reasoning: { type: 'string' },
            },
            required: ['improvement', 'reasoning'],
          },
        }
      );

      if (improvement.improvement === 'none') {
        // The honest early-out: bank the decline, exit DONE with rounds
        // unspent — "improved until honestly done" beats "improved until
        // the money ran out".
        await agent(
          `cd ${repo}, git add ${boundary.proposal_dir} ` +
            '.farnsworth/improvement-briefing.md and commit: "Good news, ' +
            `everyone! improvement round ${boundary.round} declined: ` +
            'nothing left worth a round".',
          { model: 'haiku' }
        );
        return {
          exit: 'DONE',
          iterations: i,
          improvement_rounds: improvementsBanked,
          declined_round: improvement.reasoning,
          reasoning: attestation.reasoning,
        };
      }

      // Trust-layer validation: append-only amendment, well-formed
      // collision-free checks. Exit 1 = the improver broke its artifact
      // contract; re-spawn it, never hand-patch a proposal.
      await agent(
        `cd ${repo} && run \`${pp}python3 -m farnsworth improve --apply ` +
          `${boundary.proposal_dir} --json${cfg}\`. Exit 0: git add the ` +
          'goal brief, the config, .farnsworth/improvement-briefing.md ' +
          `and ${boundary.proposal_dir}, then commit: "Good news, ` +
          `everyone! improvement round ${boundary.round} armed: <one ` +
          'line from proposal.md>". Exit 1 or 2: report the error ' +
          'verbatim and do NOT commit.',
        { model: 'haiku' }
      );
      improvementsBanked += 1;
      // The bar moved: the done-check series restarts, the proposal is
      // the next instruction, and the loop goes again.
      bestPassCount = -1;
      stalls = 0;
      gap =
        `improvement round ${boundary.round} raised the bar: ` +
        improvement.reasoning;
    } else {
      gap = attestation.reasoning; // semantic gap -> the next instruction
    }
  }

  // ---- STALLED: 3 consecutive passes without measurable progress ----
  const passCount = probe.results.filter((r) => r.exit_code === 0).length;
  if (passCount > bestPassCount) {
    bestPassCount = passCount;
    stalls = 0;
  } else {
    stalls += 1;
  }
  if (stalls >= 3) {
    return {
      exit: 'STALLED',
      iterations: i,
      note:
        '3 consecutive iterations without progress on the done checks ' +
        '— automatic escalation, never silent spinning',
    };
  }

  // ---- PREMISE: the Professor creates the next mission ----
  // (Farnsworth's role is to create the premise; the crew implements
  // it; the end of the cycle judges whether it advanced the goal.)
  phase(`Premise ${i}`);
  const derived = await agent(
    `You create the PREMISE of this cycle. cd ${repo}. Re-read the ` +
      'goal brief (GOAL.md / the goal entry in the fleet config) ' +
      'against the CURRENT merged state and the latest ' +
      '.farnsworth/done-checks.json' +
      (gap ? `, plus this attested semantic gap: "${gap}"` : '') +
      '. Write ONE new task brief at tasks/task-NNN.md (next free ' +
      'number): the SMALLEST coherent slice of the goal gap that is ' +
      'independently gateable and reviewable — never the whole gap by ' +
      'default, and never a pre-authored pipeline of future tasks. ' +
      'Append one orchestrator-log entry to ' +
      '.farnsworth/orchestrator-log.md (what the probe showed, what ' +
      'this premise targets). git add both and commit: "Good news, ' +
      'everyone! <the premise, one line>". Return the brief path and ' +
      'task id.',
    {
      model: 'sonnet',
      schema: {
        type: 'object',
        properties: {
          brief: { type: 'string' },
          task_id: { type: 'string' },
        },
        required: ['brief', 'task_id'],
      },
    }
  );

  // ---- TASK: the two-round tournament, nested (max 1 level) ----
  phase(`Task ${i}`);
  try {
    const result = await workflow('farnsworth-task', {
      repo,
      brief: derived.brief,
      farnsworthPath: args.farnsworthPath,
      config: args.config,
      fleet: args.fleet,
    });
    if (result && result.verdict && result.verdict.outcome === 'escalate') {
      return {
        exit: 'ESCALATED',
        iterations: i,
        change_request: result.verdict.reasoning,
      };
    }
    gap = null; // merged: the next probe re-measures from scratch
  } catch (err) {
    const msg = String((err && err.message) || err);
    if (msg.toLowerCase().includes('escalat')) {
      return { exit: 'ESCALATED', iterations: i, change_request: msg };
    }
    // A failed task (nothing adoptable, refuted verdict, dead fleet)
    // is a no-progress iteration: it feeds the stall counter and the
    // next Derive sees the same gap — usually the cue to slice smaller.
    stalls += 1;
    if (stalls >= 3) {
      return { exit: 'STALLED', iterations: i, note: msg };
    }
  }
}

return {
  exit: 'STOPPED',
  iterations: maxIterations,
  improvement_rounds: improvementsBanked,
  note: 'iteration budget exhausted (human-set cap, not goal completion)',
};
