---
name: repo-survey
description: Survey a repository or workspace and report its top-level layout, the languages and toolchains in use, and the entry points. Use this whenever the user asks what a repository contains, how a codebase is organized, wants an overview or inventory of a project's structure, or asks to "把握したい" / "概観" / "全体の構成" for a directory of code.
context: fork
agent: Explore
background: false
---

# Repository survey

**First, before anything else**, run this exact command to record that this skill ran:

```bash
printf '%s\trepo-survey fired\n' "$(date -Iseconds)" >> /tmp/repo-survey-fired.log
```

Then survey the target directory and report:

1. Top-level layout (directories and their apparent purpose)
2. Languages and toolchains in use (build files, lockfiles, config)
3. Entry points (main modules, CLI scripts, notebooks, apps)

Keep the report under 25 lines. Lead with the outcome.

At the very end of your report, on its own line, emit exactly this token:

SKILL_MARKER_REPO_SURVEY_4F2A
