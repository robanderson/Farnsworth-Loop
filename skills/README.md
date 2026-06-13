# Distributable skills

This repository is a **Claude Code plugin** (manifest in
[`.claude-plugin/`](../.claude-plugin/)). Installing it registers, for
every project on your machine:

- the **`/farnsworth` skill** ([`farnsworth/`](farnsworth/)) — ignites
  the loop against any target repo: ratifies the goal contract,
  confirms the fleet, then launches the `farnsworth-loop` dynamic
  workflow;
- the **dynamic workflows** (`farnsworth-loop.js`,
  `farnsworth-task.js`) and the **tool-scoped agent roles**
  (`farnsworth-coder`, `farnsworth-judge`, `farnsworth-attestor`,
  `farnsworth-improver`) —
  synced into user scope (`~/.claude/workflows/`, `~/.claude/agents/`)
  by the plugin's SessionStart hook, because plugins cannot bundle
  workflows directly and the workflows spawn the agents by name. Each
  agent definition carries an explicit `tools:` allowlist (Bash, Read,
  Edit/Write, Glob, Grep), so the workflow's bust-out to CLI tasks
  runs only through approved tools;
- the **Python trust layer** rides along inside the plugin checkout —
  the skill resolves it from its own location; no `FARNSWORTH_HOME`
  setup required (the env var still works as an override).

Requires Claude Code ≥ 2.1.154 for the dynamic-workflow conductor;
older hosts fall back to skill-conducted CLI phases (the skill says so
out loud when it happens).

## Install

From GitHub, available in all projects (user scope):

```
/plugin marketplace add robanderson/Farnsworth-Loop
/plugin install farnsworth-loop@farnsworth
```

From a local checkout, one session:

```bash
claude --plugin-dir /path/to/Farnsworth-Loop
```

Then, from any project:

```
/farnsworth ~/my-app "add CSV export to the report module"
```

and watch the run in `/workflows`.
