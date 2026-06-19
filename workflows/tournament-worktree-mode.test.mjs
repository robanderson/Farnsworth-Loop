// Structural regression tests for Phase 1 repoMode worktree attempts.
//
// node tournament-worktree-mode.test.mjs   (no deps; exits 0 on pass, 1 on fail)
//
// These are pure source/snippet assertions, matching the existing tournament tests:
//   (1) repoMode:false keeps legacy cmdHead/brief/staging snippets byte-identical.
//   (2) repoMode:true brief tells workers to edit the checkout, not propose, and forbids git/tests.
//   (3) repoMode:true staging captures `git diff <base> HEAD` and preserves FLV/provenance fail-closed flow.
//   (4) worktree setup is gated and uses the blind candidate label, never displayModel.

import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const HERE = dirname(fileURLToPath(import.meta.url))
const SRC = readFileSync(join(HERE, 'tournament.mjs'), 'utf8')

let failed = 0
const check = (name, cond) => { if (cond) console.log(`ok   - ${name}`); else { console.error(`FAIL - ${name}`); failed++ } }

function extractFn(src, name) {
  const sig = `function ${name}(`
  const start = src.indexOf(sig)
  if (start < 0) throw new Error(`could not find ${sig}`)
  let i = src.indexOf('{', start), depth = 0
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++
    else if (src[i] === '}') { depth--; if (depth === 0) return src.slice(start, i + 1) }
  }
  throw new Error(`unbalanced braces extracting ${name}`)
}

console.log('== tournament.mjs repoMode worktree phase 1 ==')

const briefSrc = extractFn(SRC, 'brief')
const stageSrc = extractFn(SRC, 'stageAndValidate')
const buildSrc = extractFn(SRC, 'buildWorktrees')
const setupSrc = extractFn(SRC, 'worktreeSetupShell')

// (1) Legacy snippets: these exact strings are the current repoMode:false behavior.
check('(legacy) repoMode flag read from args',
  SRC.includes('const repoMode = A.repoMode === true'))
check('(legacy) baseRef read from args',
  SRC.includes('const baseRef = A.baseRef || null'))
check('(legacy) cmdHead is byte-identical',
  SRC.includes("const cmdHead = (ws, b) => `mkdir -p ${q(ws)} && cd ${q(ws)} && printf '%s' ${q(b)} > _brief.txt`"))
check('(legacy) self-contained brief opening unchanged',
  briefSrc.includes('return `You are solving a self-contained task. Produce ONE complete solution in a single focused pass.'))
check('(legacy) self-contained save-dir line unchanged',
  briefSrc.includes('- Save all deliverable files to: ${ws}'))
check('(legacy) file-staging copy snippet unchanged',
  stageSrc.includes('mkdir -p ${q(dest)}; cp -R ${q(c.ws)}/. ${q(dest)}/ 2>/dev/null;'))
check('(legacy) file-staging pool concat snippet unchanged',
  stageSrc.includes('find ${q(dest)} -type f -print0 2>/dev/null | xargs -0 cat 2>/dev/null'))

// (2) Repo-anchored worker brief: apply real changes, no proposals, no tests, no git.
check('(brief) repoMode branch exists',
  briefSrc.includes('if (repoMode)'))
check('(brief) says existing git repository checkout',
  briefSrc.includes('You are working INSIDE an existing git repository checked out at: ${ws}'))
check('(brief) says apply directly to real files',
  briefSrc.includes('Apply your change DIRECTLY to the real files'))
check('(brief) forbids proposal deliverable',
  briefSrc.includes('Do NOT write a "proposal"'))
check('(brief) forbids tests',
  briefSrc.includes('Do NOT run the test suite'))
check('(brief) forbids git commands',
  briefSrc.includes('Do NOT run any git command'))
check('(brief) explains harness snapshot',
  briefSrc.includes('The harness snapshots your working tree into a commit for you after you stop.'))
check('(brief) asks for attempt notes',
  briefSrc.includes('FL-ATTEMPT-NOTES.md'))
check('(brief) still includes task text',
  briefSrc.includes('Task:\n${task}'))

// (3) Diff staging: diff-only artifact, same line protocol and provenance contract.
check('(stage) repoMode diff uses git diff base HEAD',
  stageSrc.includes('git -C ${q(c.ws)} diff ${q(baseSha)} HEAD --no-color --no-prefix > ${q(diffPath)}'))
check('(stage) diff artifact is candidate.diff',
  stageSrc.includes('const diffPath = `${dest}/candidate.diff`'))
check('(stage) D is based on non-empty diff',
  stageSrc.includes('if [ -s ${q(diffPath)} ]; then D=1; else D=0; fi'))
check('(stage) FLV line protocol preserved',
  stageSrc.includes('echo "FLV ${c.blind} d=$([ "$D" -gt 0 ] && echo 1 || echo 0) p=$P"'))
check('(stage) provenance builder still used',
  stageSrc.includes('const provChk = provCheckShell(log, tok, lp, !!c.carriedOver)'))
check('(stage) fail-closed validity still requires deliverable and provenance',
  stageSrc.includes('const valid = !!(r && r.deliverable && r.provenance)'))
check('(stage) carried-over winner reuses saved diff',
  stageSrc.includes('cp ${q(`${c.ws}/candidate.diff`)} ${q(diffPath)}'))
check('(stage) blindFail remains present for summaries',
  SRC.includes("const blindFail = r => r ? 'excluded (did not pass validation)' : r"))

// (4) Worktree creation: mode-gated, serial shell, blind labels only.
check('(worktree) buildWorktrees skips when repoMode false',
  buildSrc.includes('if (!repoMode) return'))
check('(worktree) setup uses candidate label in branch',
  setupSrc.includes('const branch = worktreeBranch(roundName, c.label)'))
check('(worktree) setup does not mention displayModel',
  !setupSrc.includes('displayModel'))
check('(worktree) branch namespace is flwt/run/round/label',
  SRC.includes('`flwt/${safeRunId}/${roundName}/${label}`'))
check('(worktree) git worktree add is serial shell, not parallel dispatch',
  setupSrc.includes('git worktree add -b "$branch" "$ws" "$baseSha" --no-checkout'))
check('(worktree) engine logs excluded before worker runs',
  setupSrc.includes('rev-parse --git-path info/exclude') && setupSrc.includes('Farnsworth Loop engine files'))
check('(worktree) harness commit uses fixed identity',
  SRC.includes('GIT_AUTHOR_NAME=farnsworth GIT_AUTHOR_EMAIL=farnsworth@localhost') &&
  SRC.includes('GIT_COMMITTER_NAME=farnsworth GIT_COMMITTER_EMAIL=farnsworth@localhost'))
check('(worktree) base date cached once',
  SRC.includes('dateFile=${q(dateFile)}') && SRC.includes('git show -s --format=%cI "$baseSha"'))

console.log(failed ? `\n${failed} check(s) FAILED` : '\nAll checks passed')
process.exit(failed ? 1 : 0)
