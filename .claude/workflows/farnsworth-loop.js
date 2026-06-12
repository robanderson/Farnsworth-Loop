// The Farnsworth LOOP as a Claude Code dynamic workflow — the OUTER
// cycle that makes it a loop at all: a -> b -> c -> a.
//
//   probe the goal -> derive the smallest next task -> run the
//   two-round tournament (nested farnsworth-task workflow) -> merge ->
//   inspect against the goal -> GO AGAIN, with the attested gap as the
//   next instruction — until DONE, ESCALATED, STOPPED, or STALLED
//   (PRD Section 2.4: exactly four exits, every one recorded).
//
// Iteration count is EMERGENT: nothing here pre-authors a task list.
// Each pass derives one task — the smallest coherent slice of the goal
// gap that is independently gateable — and the next pass re-reads the
// goal against the newly merged state.
//
// Launch with args, e.g.:
//   { repo: '/abs/path/to/project', farnsworthPath: '/path/to/Farnsworth-Loop',
//     maxIterations: 8, fleet: [...], config: 'farnsworth.json' }
// Requires a `goal` entry (done checks) in the fleet config — a loop
// without a termination contract either stops early or never.

export const meta = {
  name: 'farnsworth-loop',
  description:
    'The goal cycle: probe done -> derive the smallest next task -> ' +
    'nested farnsworth-task tournament -> merge -> attest -> loop. ' +
    'Exits DONE / ESCALATED / STOPPED / STALLED, all recorded.',
  phases: [
    { title: 'Probe' },
    { title: 'Premise' },
    { title: 'Task' },
    { title: 'Attest' },
  ],
};

const repo = args.repo;
const pp = args.farnsworthPath ? `PYTHONPATH=${args.farnsworthPath} ` : '';
const cfg = args.config ? ` --config ${args.config}` : '';
const maxIterations = args.maxIterations || 8; // the STOPPED budget

let stalls = 0; // consecutive iterations without done-check progress
let bestPassCount = -1;
let gap = null; // the attestor's named gap = the next instruction

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
      return { exit: 'DONE', iterations: i, reasoning: attestation.reasoning };
    }
    gap = attestation.reasoning; // semantic gap -> the next instruction
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
  note: 'iteration budget exhausted (human-set cap, not goal completion)',
};
