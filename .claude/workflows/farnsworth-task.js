// Farnsworth task as a Claude Code DYNAMIC WORKFLOW — the full v2
// two-round spine (PRD Section 2): ROUND 1 explore -> DISTILL ->
// ROUND 2 informed rebuild, with the champion mechanism and an
// adversarial Verify before finalize.
//
// Division of labor (PRD 4.1c-ii): this script is the CONDUCTOR; the
// Python CLI is the TRUST layer (worktrees, gates, anonymization,
// artifacts — agents run it via Bash and relay its --json records
// verbatim); the .claude/agents roles supply JUDGMENT. Until M7
// mechanizes the v2 schema in the CLI, this script conducts the PRD's
// documented manual protocol: each round is a CLI task, lessons are
// installed between rounds, and the champion is relabeled into the
// round-2 review field by the conductor's agents (PRD 2.2, M7 note).
//
// THE FLEET IS DYNAMIC, DECIDED AT LAUNCH — never assume the config's
// default field. The runtime takes no mid-run input, so the conductor
// session must confirm the fleet with the human BEFORE launching, then
// pass it in args:
//   - args.fleet:  a workers array (delegate `model` entries for Claude
//     models; `command` entries for the third-party/local adapter — GLM,
//     MiniMax, Qwen, Codex, Ollama / LM Studio / MLX). The Fleet phase
//     writes it to a run-scoped config, merged with the repo config's
//     reviewer/gate/goal. One dispatch mode per fleet (PRD 4.1b).
//   - args.config: path to an existing alternate fleet config.
//   - neither: the repo's farnsworth.json, surfaced in the Fleet phase
//     so the choice is visible in /workflows, not silent.
//
// Launch with args, e.g.:
//   { repo: '/home/user/word-garden-6', brief: 'tasks/task-001.md',
//     farnsworthPath: '/home/user/Farnsworth-Loop',
//     fleet: [{ id: 'w1', model: 'claude-haiku-4-5' },
//             { id: 'w2', model: 'claude-sonnet-4-6' }] }
// Monitor in /workflows (p pause, x stop, s save). Syntax per
// code.claude.com/docs/en/workflows (June 2026).

export const meta = {
  name: 'farnsworth-task',
  description:
    'One Farnsworth Loop task, two-round v2 spine: blind explore round ' +
    '-> distill lessons -> clean-slate informed rebuild judged blind ' +
    'against the round-1 champion -> adversarial verify -> finalize',
  phases: [
    { title: 'Fleet' },
    { title: 'R1 Prepare' },
    { title: 'R1 Explore' },
    { title: 'R1 Gate' },
    { title: 'R1 Judge' },
    { title: 'Distill' },
    { title: 'R2 Rebuild' },
    { title: 'R2 Gate' },
    { title: 'R2 Judge' },
    { title: 'Verify' },
    { title: 'Finalize' },
  ],
};

const repo = args.repo;
const brief = args.brief;
const pp = args.farnsworthPath ? `PYTHONPATH=${args.farnsworthPath} ` : '';
const taskId = brief.split('/').pop().replace(/\.md$/, '');
const r2Brief = brief.replace(/\.md$/, '-r2.md');
const r2TaskId = `${taskId}-r2`;
// The champion enters round 2's review field under a fixed spare label;
// the verdict-2 judge sees only one more candidate among candidates.
const CHAMPION_LABEL = 'Z';
// Run-scoped fleet: args.fleet writes a config; args.config names one;
// otherwise the repo default applies (and is surfaced, never silent).
const fleetConfig = args.fleet
  ? `.farnsworth/fleet-${taskId}.json`
  : args.config || null;
const cfg = fleetConfig ? ` --config ${fleetConfig}` : '';

function tier(modelId) {
  if (modelId.includes('haiku')) return 'haiku';
  if (modelId.includes('sonnet')) return 'sonnet';
  if (modelId.includes('fable')) return 'fable';
  return 'opus';
}

const ledgerSchema = {
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
};

const gateSchema = {
  type: 'object',
  properties: {
    exit_code: { type: 'number' },
    phase: { type: 'string' },
    reviewer_model: { type: 'string' },
    review_env: { type: 'string' },
    review_briefing: { type: 'string' },
  },
  required: ['exit_code', 'phase'],
};

function prepare(briefPath, id) {
  return agent(
    `cd ${repo} && run \`${pp}python3 -m farnsworth run ${briefPath} ` +
      `--json${cfg}\`. Exit code 3 is SUCCESS (a phase boundary: coder agents ` +
      'are next). If it exits 2 with a collision error, run ' +
      `\`${pp}python3 -m farnsworth clean ${id}\` once and retry. ` +
      'Relay the JSON it printed VERBATIM.',
    { model: 'haiku', schema: ledgerSchema }
  );
}

function dispatchCoders(ledger, id, roundNote) {
  return parallel(
    ledger.workers.map((w) => () =>
      agent(
        `You are worker ${w.id} (a farnsworth-coder) in a blind ` +
          `tournament round. ${roundNote} cd into your worktree ` +
          `${w.worktree_abs} (branch ${w.branch}) FIRST and work only ` +
          `there. Your briefing is the file ` +
          `${repo}/.farnsworth/${id}/briefings/${w.id}.md — read it ` +
          'first and follow it exactly. Read no other file under ' +
          '.farnsworth/ (you work blind). Time-box: one complete honest ' +
          'attempt, then COMMIT; if something still fails after a couple ' +
          'of fix passes, commit what you have and note the gap in the ' +
          'commit message. The committed diff is the deliverable; never ' +
          'delegate.',
        { agent: 'farnsworth-coder', model: tier(w.model) }
      )
    )
  );
}

function runGate(id) {
  return agent(
    `cd ${repo} && run \`${pp}python3 -m farnsworth gate ${id} --json${cfg}\` ` +
      '(per-worker progress streams on stderr; one JSON object lands on ' +
      'stdout). Exit 3 means candidates are ready; exit 1 means none ' +
      'passed; exit 2 is an error. Report the exit code and relay the ' +
      'JSON VERBATIM.',
    { model: 'haiku', schema: gateSchema }
  );
}

// ---------------- FLEET (dynamic, resolved before any token spends) ----
phase('Fleet');
const fleetReport = await agent(
  `cd ${repo}. ` +
    (args.fleet
      ? `Write ${fleetConfig}: take the repo's farnsworth.json, replace ` +
        `its "workers" with exactly ${JSON.stringify(args.fleet)} ` +
        '(keep reviewer, gate, and goal as they are; every worker needs ' +
        'an id, and either "model" — delegate dispatch — or "command" ' +
        'with a {prompt} token — the third-party/local adapter; one ' +
        'dispatch mode for the whole fleet). '
      : `Read ${fleetConfig || 'farnsworth.json'}. `) +
    `Then run \`${pp}python3 -m farnsworth preflight${cfg}\`. Report the ` +
    'resolved fleet (one entry per worker: id, dispatch mode, ' +
    'model-or-command, focus) and the preflight outcome. A gate-at-base ' +
    'failure in a greenfield repo (the package under test does not ' +
    'exist yet) is a documented false positive: note it, set fatal ' +
    'false. Any config, git, or canary failure is fatal.',
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
              dispatch: { type: 'string', enum: ['delegate', 'subprocess'] },
              spec: { type: 'string' },
              focus: { type: ['string', 'null'] },
            },
            required: ['id', 'dispatch', 'spec'],
          },
        },
        preflight: { type: 'string' },
        fatal: { type: 'boolean' },
      },
      required: ['workers', 'preflight', 'fatal'],
    },
  }
);
if (fleetReport.fatal) {
  throw new Error(
    `fleet preflight failed: ${fleetReport.preflight} — fix the fleet ` +
      'config before dispatching a tournament'
  );
}
if (fleetReport.workers.some((w) => w.dispatch === 'subprocess')) {
  // A `command` fleet is driven end-to-end by `farnsworth run` itself
  // (the CLI spawns, gates, and reviews its own subprocesses); this
  // phased script is the conductor for delegate fleets. Workflow
  // conduction of subprocess/local fleets is queued in M8.
  throw new Error(
    'this fleet uses the subprocess adapter (third-party/local CLIs): ' +
      `run it end-to-end with \`${pp}python3 -m farnsworth run ${brief}` +
      `${cfg}\` per round instead of this workflow`
  );
}

// ---------------- ROUND 1 — EXPLORE ----------------
phase('R1 Prepare');
const r1Ledger = await prepare(brief, taskId);

phase('R1 Explore');
await dispatchCoders(
  r1Ledger,
  taskId,
  'This is ROUND 1 of a two-round task: EXPLORE. Wide and instructive ' +
    'beats narrow and perfect; the field is judged by what it teaches ' +
    'as much as by what it ships.'
);

phase('R1 Gate');
const r1Gate = await runGate(taskId);
if (r1Gate.exit_code !== 3) {
  // Until M7 lands gate-as-evidence in the CLI, a no-candidate round 1
  // cannot reach review; surface it rather than improvising (a lessons-
  // only round 2 needs the judge to have seen the failures).
  throw new Error(
    `round-1 gate exited ${r1Gate.exit_code} (phase=${r1Gate.phase}): ` +
      'no reviewable candidates — clean and re-dispatch round 1'
  );
}

phase('R1 Judge');
const verdict1 = await agent(
  `You are the farnsworth-judge for ROUND 1 of a two-round task. cd ` +
    `into the review environment ${r1Gate.review_env} FIRST and work ` +
    `only there. Your briefing is ${repo}/${r1Gate.review_briefing} — ` +
    'follow its Review Protocol exactly (blind sketch BEFORE reading ' +
    'candidates; empirical probes; review.md; code-tips.next.md; ' +
    'seed-tips.next.md; verdict.json LAST). Round-1 framing: your ' +
    '"adopt" candidate is the CHAMPION — it survives unchanged into ' +
    "round 2's review field; it does NOT merge yet. Distill hard: " +
    'round 2 rebuilds from your lessons alone. Set round_2 to ' +
    '"proceed" unless the champion is clean AND the field taught ' +
    'nothing worth a rebuild ("adopt-final" carries the burden of ' +
    'proof) or the task spec itself is broken ("escalate").',
  {
    agent: 'farnsworth-judge',
    model: tier(r1Ledger.reviewer_model),
    schema: {
      type: 'object',
      properties: {
        outcome: { type: 'string', enum: ['adopt', 'synthesize', 'escalate'] },
        candidate: { type: ['string', 'null'] },
        reasoning: { type: 'string' },
        round_2: {
          type: 'string',
          enum: ['proceed', 'adopt-final', 'escalate'],
        },
      },
      required: ['outcome', 'candidate', 'reasoning', 'round_2'],
    },
  }
);
if (verdict1.round_2 === 'escalate' || verdict1.outcome === 'escalate') {
  throw new Error(
    `round-1 escalation: ${verdict1.reasoning} — relay the change ` +
      'request to the human; hints never silently amend the contract'
  );
}
const champion =
  verdict1.outcome === 'adopt' ? verdict1.candidate : null; // none = lessons-only rebuild

// ---------------- DISTILL (lessons travel; code does not) ----------------
phase('Distill');
await agent(
  `cd ${repo} && finalize round 1 and install its lessons: run ` +
    `\`${pp}python3 -m farnsworth finalize ${taskId} --json\`. Then, if ` +
    `.farnsworth/${taskId}/code-tips.next.md exists, copy it over ` +
    `.code-tips.md. Create ${r2Brief} as an exact copy of ${brief} ` +
    'with one line appended at the top: "(Round 2 of ' +
    `${taskId}: informed rebuild — your briefing tips include round-1's ` +
    'distilled lessons. Clean slate: design from the brief and the ' +
    'lessons.)". git add .code-tips.md ' +
    `${r2Brief} .farnsworth/${taskId} and commit with message ` +
    `"Good news, everyone! ${taskId} round-1 lessons installed". ` +
    'Do NOT copy any round-1 code anywhere: lessons travel, diffs do not.',
  { model: 'haiku' }
);

if (verdict1.round_2 === 'adopt-final') {
  // The justified skip (PRD 2.2): adopt the champion now; Verify still runs.
  phase('Verify');
  const v = await verifyVerdict(taskId, r1Gate.review_env, verdict1);
  phase('Finalize');
  return await finalizeAndAdopt(taskId, verdict1, v, {
    note: 'adopt-final: round 2 skipped on judge attestation',
  });
}

// ---------------- ROUND 2 — INFORMED REBUILD ----------------
phase('R2 Rebuild');
const r2Ledger = await prepare(r2Brief, r2TaskId);
await dispatchCoders(
  r2Ledger,
  r2TaskId,
  'This is ROUND 2 of a two-round task: INFORMED REBUILD. Your tips ' +
    "file carries round 1's distilled lessons; build the better " +
    'implementation they point at. You never see round-1 code.'
);

phase('R2 Gate');
const r2Gate = await runGate(r2TaskId);
if (r2Gate.exit_code !== 3 && !champion) {
  throw new Error(
    `round-2 gate exited ${r2Gate.exit_code} and there is no champion: ` +
      'nothing adoptable — distill again and dispatch round 3, or escalate'
  );
}

// Champion relabeling, by hand until M7 (PRD 2.2): the round-1 winner
// joins the round-2 review field under a spare label, unattributed.
if (champion) {
  await agent(
    `Champion relabel for ${r2TaskId} (mechanical; copy EXACTLY, edit ` +
      `nothing else): copy ${repo}/.farnsworth/${taskId}/candidates/` +
      `${champion}.diff to ${repo}/.farnsworth/${r2TaskId}/candidates/` +
      `${CHAMPION_LABEL}.diff AND to ${r2Gate.review_env}/.farnsworth/` +
      `${r2TaskId}/candidates/${CHAMPION_LABEL}.diff. Then append this ` +
      `line to the Candidates list in ${repo}/${r2Gate.review_briefing} ` +
      'and to the copy of that briefing inside the review environment ' +
      'if one exists: "- Candidate ' +
      `${CHAMPION_LABEL}: .farnsworth/${r2TaskId}/candidates/` +
      `${CHAMPION_LABEL}.diff". Reveal nowhere that it is round-1's ` +
      'champion: it must read as one more candidate.',
    { model: 'haiku' }
  );
}

phase('R2 Judge');
const verdict2 = await agent(
  `You are the farnsworth-judge. cd into the review environment ` +
    `${r2Gate.review_env} FIRST and work only there. Your briefing is ` +
    `${repo}/${r2Gate.review_briefing} — follow its Review Protocol ` +
    'exactly (blind sketch first; empirical probes; review.md; ' +
    'code-tips.next.md; seed-tips.next.md; verdict.json LAST). Judge ' +
    'every candidate on the brief alone; never guess authorship, model, ' +
    'or round.',
  {
    agent: 'farnsworth-judge',
    model: tier(r2Ledger.reviewer_model),
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

phase('Verify');
const verification = await verifyVerdict(
  r2TaskId,
  r2Gate.review_env,
  verdict2
);

phase('Finalize');
const championSurvived = champion && verdict2.candidate === CHAMPION_LABEL;
if (championSurvived) {
  // Negative learning result (PRD 2, verdict-2): the informed rebuild
  // failed to beat blind exploration. Recorded, never hidden; the merge
  // happens through round 1's task, whose ledger knows the champion.
  return await finalizeAndAdopt(taskId, verdict1, verification, {
    note:
      'NEGATIVE RESULT: champion survived verdict-2 — informed rebuild ' +
      'did not beat blind exploration. Record in the orchestrator log ' +
      'and metrics.',
    verdict2,
  });
}
return await finalizeAndAdopt(r2TaskId, verdict2, verification, {
  verdict1,
  champion_fate: champion ? 'beaten by the rebuild' : 'no champion',
});

// ---------------- helpers ----------------
async function verifyVerdict(id, reviewEnv, verdict) {
  const v = await agent(
    `You are an independent verifier; you are NOT the judge and must ` +
      `not defer to it. cd into ${reviewEnv} and work only there. The ` +
      `verdict under test: ${JSON.stringify(verdict)}. Read ` +
      `.farnsworth/${id}/review.md, extract the verdict's LOAD-BEARING ` +
      'claims, then attack them empirically: apply the relevant ' +
      "candidate diff with `git apply`, run the project's tests and the " +
      'specific scenarios the claims rest on, and actively try to ' +
      'refute each claim. Return to base with `git reset --hard && git ' +
      'clean -fd -e .farnsworth` when done. Never edit review artifacts.',
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
  if (v.check === 'refuted') {
    throw new Error(
      'verdict REFUTED by independent verification: ' +
        v.evidence.join(' | ') +
        ' — re-run the judge phase with the refutation in hand'
    );
  }
  return v;
}

async function finalizeAndAdopt(id, verdict, verification, extra) {
  const summary = await agent(
    `cd ${repo} && run \`${pp}python3 -m farnsworth finalize ${id} ` +
      `--json\` (exit 0 expected; if it exits 2 the verdict artifact is ` +
      'missing/malformed — report that verbatim instead of improvising), ' +
      `then \`${pp}python3 -m farnsworth report ${id}\` and output the ` +
      'report table verbatim.' +
      (verdict.outcome === 'adopt'
        ? ` Then run \`${pp}python3 -m farnsworth adopt ${id} --clean\` ` +
          'and relay its output (tips install, seed-tips routing, ' +
          'consolidation notice).'
        : ''),
    { model: 'haiku' }
  );
  return { task: id, verdict, verification, summary, ...extra };
}
