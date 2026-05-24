# special-agents

Project-level `.claude/` setup for a plan/implement/review pipeline:

1. `/implement` enters plan mode in a worktree.
2. On `ExitPlanMode`, the plan is gated through:
   - **Self-review** loop (up to 7 passes; ends when the plan contains `<!-- review-clean -->`).
   - **Clarity check** via the `plan-clarity-reviewer` sub-agent, producing an ambiguity score (`<!-- ambiguity: N -->`).
3. Implementation is routed by score:
   - 1–6 → `junior-plan-implementer` sub-agent on Sonnet.
   - 7–10 → lead (current session) implements directly on Opus.
4. `/review` runs the `plan-implementation-reviewer` sub-agent and pipes findings back.

Every prompt is prefixed with five behavioral rules (ultrathink, simplicity, no comments, conciseness, no assumptions). Sub-agents on light models get a trimmed variant.

## Install in a project

Drop the `.claude/` directory at the root of the consuming project (or `git clone` this repo into the project as `.claude/`):

```bash
git clone https://github.com/semihkayan/claude-special-agents.git .claude
```

Restart Claude Code (or `/reload-plugins`) so the hooks register.

## Layout

```
.claude/
  settings.json                 hooks wiring + recommended env
  agents/
    junior-plan-implementer.agent.md
    plan-clarity-reviewer.agent.md
    plan-implementation-reviewer.agent.md
  commands/
    implement.md
    review.md
  hooks/special-agents/
    _lib.py
    inject-base-rules.py            UserPromptSubmit
    inject-rules-into-subagent.py   PreToolUse[Agent]
    plan-review-gate.py             PreToolUse[ExitPlanMode]
    implementation-router.py        PostToolUse[ExitPlanMode]
    discard-state.py                PreToolUse[EnterPlanMode]
```

## State

- Per-session JSON at `.claude/hooks/special-agents/state/session-<id>.json`, 1-hour TTL, swept on each `ExitPlanMode`.
- Fallback plan copies (when the harness doesn't supply `planFilePath` in the `ExitPlanMode` tool call) at `.claude/hooks/special-agents/plans/session-<id>.md`.

Add to the consuming project's `.gitignore`:

```
.claude/hooks/*/state/
.claude/hooks/special-agents/plans/
.claude/plans/
```

## Optional settings

`settings.json` ships with `"plansDirectory": ".claude/plans"`, which tells the harness to give Claude a stable plan-file path. The hooks work without it — they fall back to writing the plan under `.claude/hooks/special-agents/plans/` — but a stable path is nicer if you want to browse plans.

The bundled `env` block (`MAX_THINKING_TOKENS`, `CLAUDE_CODE_MAX_OUTPUT_TOKENS`, etc.) mirrors the original development environment. Strip what you don't want.
