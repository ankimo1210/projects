---
name: repo-survey
description: Survey a repository or workspace and report its top-level layout, the languages and toolchains in use, and the entry points. Use this whenever the user asks what a repository contains, how a codebase is organized, wants an overview or inventory of a project's structure, or asks to "把握したい" / "概観" / "全体の構成" for a directory of code.
context: fork
agent: Explore
background: false
---

# Repository survey

Survey the target directory and report:

1. Top-level layout (directories and their apparent purpose)
2. Languages and toolchains in use (build files, lockfiles, config)
3. Entry points (main modules, CLI scripts, notebooks, apps)

Respect the repository's agent guide: skip the directories it excludes from
inspection (for example `.agentignore`), and do not read lock files or heavy
data files.

Keep the report under 25 lines. Lead with the outcome.
