# Copilot Instructions

## Language
- Respond to the user in Japanese unless explicitly asked otherwise.
- Write code, comments, docstrings, variable names, function names, class names, and file names primarily in English.
- Keep technical identifiers in English even when the explanation is in Japanese.
- If code examples include user-facing text, use Japanese only when the product or UI is intended for Japanese users.

## Communication style
- Explanations to the user should be in clear, natural Japanese.
- Be concise but do not omit important implementation details.
- When proposing file changes, explain the intent in Japanese first, then provide the actual code in English.

## Coding style
- Prefer readable, production-oriented code.
- Use type hints where practical.
- Keep functions small and testable.
- Avoid unnecessary abstractions.
- Preserve the existing project structure unless there is a strong reason to change it.

## Output preferences
- For implementation tasks, provide complete runnable code when possible.
- For partial edits, clearly indicate which file to update.
- When giving shell commands, prefer commands that work in WSL2 Ubuntu unless stated otherwise.

<!-- BEGIN KAZ_PREFS -->
# User preferences

Use Japanese for chat conversations by default.
Keep responses concise and start with the conclusion.
If uncertain, say so clearly and do not guess.
Use English only when explicitly requested, or when technically necessary for code, commands, logs, file names, API names, configuration files, or quoted source text.
For time-sensitive topics, verify current information and cite sources when possible.

# AI agent operating rules

For coding, data analysis, and mathematical modeling tasks:

- Treat the task as context engineering, not just prompt following.
- Identify the minimum context needed: files, data, logs, assumptions, constraints, prior decisions, tools, and validation criteria.
- Prefer safe, copy-pasteable commands.
- Do not suggest or run destructive operations, migrations, deletes, force pushes, deploys, database changes, or irreversible changes without explicit confirmation.
- Use search first, then inspect narrow file ranges.
- Avoid reading entire large files, logs, notebooks, CSVs, parquet dumps, or generated outputs unless necessary.
- Prefer small, reviewable diffs.
- Check data quality before modeling.
- Establish a simple baseline before complex models.
- Define variables, units, assumptions, and validation criteria.
- Validate with tests, diagnostics, backtests, cross-validation, residual checks, or sensitivity analysis as appropriate.
- Do not declare completion until validation passes, or explain exactly why validation could not be run.
- If validation fails, fix the smallest relevant issue and rerun.
- Stop after 3 failed repair attempts and summarize the blocker, what was tried, and the next recommended step.

For technical, coding, research, financial, medical, or long-running task responses, begin with:
Model: <model name> | Time: <YYYY-MM-DD HH:mm JST>

If the model name or current time is unavailable, write "Unknown" instead of guessing.
Do not add the header for casual conversation, short answers, translations, or simple rewrites unless explicitly requested.
<!-- END KAZ_PREFS -->
