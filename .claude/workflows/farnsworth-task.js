// Farnsworth tournament round as a Claude Code DYNAMIC WORKFLOW.
//
// This is the scripted successor to the farnsworth-task skill: the same
// five phases, but orchestrated by the workflow runtime instead of the
// host session turn-by-turn. What that buys (PRD Section 4.1c2):
//   - the coder fan-out runs under the runtime's scheduler (16-agent
//     concurrency cap, per-agent token/tool counts live in /workflows,
//     pause with p / stop with x / save with s);
//   - intermediate results live in script variables, not the
//     orchestrating session's context window;
//   - phase structure is explicit and monitorable, not narrated.
//
// The division of labor is unchanged: every mechanical phase is still the
// Python CLI (the artifact is the phase boundary, never an agent's word).
// Agents run the CLI via Bash; this script only routes prompts and JSON.
//
// Launch: /farnsworth-task-js with args, or ask Claude to run it, e.g.
//   { repo: '/home/user/word-garden-6', brief: 'tasks/task-001.md',
//     farnsworthPath: '/home/user/Farnsworth-Loop' }
// Syntax per code.claude.com/docs/en/workflows (June 2026). Inspect with
// Ctrl+G / "View raw script" before the first run.

export const meta = {
  name: 'farnsworth-task',
  description:
    'One Farnsworth Loop tournament round: prepare -> parallel blind ' +
    'coders -> mechanical gate -> anonymized judge -> adversarial ' +
    'verify -> finalize/report',
  phases: [
    { title: 'Prepare' },
    { title: 'Code' },
    { title: 'Gate' },
    { title: 'Judge' },
    { title: 'Verify' },
    { title: 'Finalize' },
  ],
};

const repo = args.repo;
const brief = args.brief;
const pp = args.farnsworthPath ? `PYTHONPATH=${args.farnsworthPath} ` : '';
const taskId = brief.split('/').pop().replace(/\.md$/, '');

// Ledger model ids -> workflow model overrides.
function tier(modelId) {
  if (modelId.includes('haiku')) return 'haiku';
  if (modelId.includes('sonnet')) return 'sonnet';
  if (modelId.includes('fable')) return 'fable';
  return 'opus';
}

// ---- Phase 1: Prepare (CLI: worktrees, briefings, dispatch ledger) ----
phase('Prepare');
const ledger = await agent(
  `cd ${repo} && run \`${pp}python3 -m farnsworth run ${brief} --json\`. ` +
    'Exit code 3 is SUCCESS (a phase boundary: coder agents are next). ' +
    'If it exits 2 with a collision error, run ' +
    `\`${pp}python3 -m farnsworth clean ${taskId}\` once and retry. ` +
    'Relay the JSON it printed VERBATIM.',
  {
    model: 'haiku',
    schema: {
      type: 'object',
      properties: {
        workers: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              id: { type: 'string' },
              model: { type: 'string' },
              branch: { type: 'string' },
              worktree_abs: { type: 'string' },
              briefing: { type: 'string' },
            },
            required: ['id', 'model', 'branch', 'worktree_abs', 'briefing'],
          },
        },
        reviewer_model: { type: 'string' },
      },
      required: ['workers', 'reviewer_model'],
    },
  }
);

// ---- Phase 2: Code (parallel, blind; one coder per ledger entry) ----
phase('Code');
await parallel(
  ledger.workers.map((w) => () =>
    agent(
      `You are worker ${w.id} (a farnsworth-coder) in a blind tournament ` +
        `round. cd into your worktree ${w.worktree_abs} (branch ` +
        `${w.branch}) FIRST and work only there. Your briefing is the ` +
        `file ${repo}/.farnsworth/${taskId}/briefings/${w.id}.md — read ` +
        'it first and follow it exactly (rules of engagement, tips, task, ' +
        'focus). Read no other file under .farnsworth/ (you work blind). ' +
        'Time-box: this is round-1 exploration — one complete honest ' +
        'attempt, then COMMIT; if something still fails after a couple of ' +
        'fix passes, commit what you have and note the gap in the commit ' +
        'message. The committed diff is the deliverable; never delegate.',
      { agent: 'farnsworth-coder', model: tier(w.model) }
    )
  )
);

// ---- Phase 3: Gate (CLI: commit check, mechanical gate, anonymize) ----
phase('Gate');
const gate = await agent(
  `cd ${repo} && run \`${pp}python3 -m farnsworth gate ${taskId} --json\` ` +
    '(per-worker progress streams on stderr; one JSON object lands on ' +
    'stdout). Exit 3 means candidates are ready; exit 1 means none ' +
    'passed; exit 2 is an error. Report the exit code and relay the JSON ' +
    'VERBATIM.',
  {
    model: 'haiku',
    schema: {
      type: 'object',
      properties: {
        exit_code: { type: 'number' },
        phase: { type: 'string' },
        reviewer_model: { type: 'string' },
        review_env: { type: 'string' },
        review_briefing: { type: 'string' },
        workers: { type: 'array' },
      },
      required: ['exit_code', 'phase'],
    },
  }
);
if (gate.exit_code !== 3) {
  throw new Error(
    `gate exited ${gate.exit_code} (phase=${gate.phase}) — no review ` +
      'phase (fix or clean + re-dispatch, then rerun)'
  );
}

// ---- Phase 4: Judge (anonymized review in the constructed env) ----
phase('Judge');
const verdict = await agent(
  `You are the farnsworth-judge. cd into the constructed review ` +
    `environment ${gate.review_env} FIRST and work only there. Your ` +
    `briefing is ${repo}/${gate.review_briefing} — read it and follow ` +
    'its Review Protocol exactly, writing every artifact at the path it ' +
    'names (blind sketch BEFORE reading candidates; empirical probes; ' +
    'review.md; code-tips.next.md; seed-tips.next.md; verdict.json ' +
    'LAST). Never guess candidate authorship.',
  {
    agent: 'farnsworth-judge',
    model: tier(ledger.reviewer_model),
    schema: {
      type: 'object',
      properties: {
        outcome: { type: 'string', enum: ['adopt', 'synthesize', 'escalate'] },
        candidate: { type: ['string', 'null'] },
        reasoning: { type: 'string' },
      },
      required: ['outcome', 'candidate', 'reasoning'],
    },
  }
);

// ---- Phase 5: Verify (fresh eyes attack the verdict's claims) ----
// The agent doing the judging must not be the last one to grade it: a
// separate verifier tries to REFUTE the verdict's load-bearing claims
// before anything merges (the June 2026 audit/judge/verify pattern).
phase('Verify');
const verification = await agent(
  `You are an independent verifier; you are NOT the judge and must not ` +
    `defer to it. cd into ${gate.review_env} and work only there. The ` +
    `verdict under test: ${JSON.stringify(verdict)}. Read ` +
    `.farnsworth/${taskId}/review.md, extract the verdict's LOAD-BEARING ` +
    'claims (what makes the chosen candidate adequate, or the spec ' +
    'broken), then attack them empirically: apply the relevant candidate ' +
    "diff with `git apply`, run the project's tests and the specific " +
    'scenarios the claims rest on, and actively try to refute each claim. ' +
    'Return to base with `git reset --hard && git clean -fd -e ' +
    '.farnsworth` when done. Never edit the review artifacts.',
  {
    model: 'sonnet',
    schema: {
      type: 'object',
      properties: {
        check: {
          type: 'string',
          enum: ['confirmed', 'overstated', 'refuted'],
        },
        evidence: { type: 'array', items: { type: 'string' } },
      },
      required: ['check', 'evidence'],
    },
  }
);
if (verification.check === 'refuted') {
  throw new Error(
    'verdict REFUTED by independent verification: ' +
      verification.evidence.join(' | ') +
      ' — re-run the Judge phase with the refutation in hand'
  );
}

// ---- Phase 6: Finalize (CLI validates the verdict artifact) ----
phase('Finalize');
const summary = await agent(
  `cd ${repo} && run \`${pp}python3 -m farnsworth finalize ${taskId} ` +
    `--json\` then \`${pp}python3 -m farnsworth report ${taskId}\`. If ` +
    'finalize exits 2 the verdict artifact is missing/malformed: report ' +
    'that verbatim instead of improvising. Output the report table ' +
    'verbatim.',
  { model: 'haiku' }
);

return {
  task: taskId,
  gate_phase: gate.phase,
  verdict,
  verification,
  summary,
  next:
    verdict.outcome === 'adopt'
      ? `${pp}python3 -m farnsworth adopt ${taskId} --clean`
      : verdict.outcome === 'synthesize'
        ? 'surface the judge synthesis for human merge'
        : 'escalation: relay the change request to the human',
};
