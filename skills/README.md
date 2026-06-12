# Distributable skills

Skills here are PORTABLE: unlike `.claude/skills/` (which only loads
inside this repository), these are meant to be installed into your
personal skill library and invoked from ANY project.

| Skill | What it does |
|---|---|
| [`farnsworth/`](farnsworth/) | The portable loop conductor: `/farnsworth <project-dir> "<goal>"` ratifies a goal contract in the target repo, then cycles smallest-slice blind tournaments until the goal is attested done. |

## Install

CLI / Claude Code:

```bash
cp -r skills/farnsworth ~/.claude/skills/farnsworth
```

Claude desktop app: Settings → Customize → Skills → add the
`skills/farnsworth` folder.

The skill drives the Python CLI in this repository; point it at your
checkout with `FARNSWORTH_HOME` (defaults to `~/Farnsworth-Loop`):

```bash
export FARNSWORTH_HOME=/path/to/Farnsworth-Loop
```
