# special-agents

Claude Code plugin. A plan/implement/review pipeline:

1. `/implement` enters plan mode in a worktree.
2. On `ExitPlanMode`, the plan is gated through:
   - **Self-review** loop (up to 7 passes; ends when plan body contains `<!-- review-clean -->`).
   - **Clarity check** via the `plan-clarity-reviewer` sub-agent, producing an ambiguity score (`<!-- ambiguity: N -->`).
3. Implementation is routed by score:
   - 1–6 → `junior-plan-implementer` sub-agent on Sonnet.
   - 7–10 → lead (current session) implements directly on Opus.
4. `/review` runs the `plan-implementation-reviewer` sub-agent and pipes findings back.

Every prompt is prefixed with five behavioral rules (ultrathink, simplicity, no comments, conciseness, no assumptions). Sub-agents on light models receive a trimmed variant.

## Contents

- `commands/` — `/implement`, `/review`
- `agents/` — `junior-plan-implementer`, `plan-clarity-reviewer`, `plan-implementation-reviewer`
- `hooks/` — state machine over `EnterPlanMode` / `ExitPlanMode` / `Agent` / `UserPromptSubmit`

## Install

```
/plugin install <path-to-this-repo>
```

Or via marketplace once published.

## Required project settings

The plugin assumes plans are written to `.claude/plans/` in the user's project (the `plan-review-gate` hook resolves the active plan path from the transcript by matching `.claude/plans/<name>.md`). Set in the consuming project's `.claude/settings.json`:

```json
{
  "plansDirectory": ".claude/plans"
}
```

## Recommended project settings

These match the original development environment but are not required:

```json
{
  "model": "claude-opus-4-7[1m]",
  "effortLevel": "max",
  "alwaysThinkingEnabled": true,
  "env": {
    "CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING": "1",
    "MAX_THINKING_TOKENS": "127999",
    "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "128000",
    "CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY": "20",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "400000",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

## State

Per-session state is written to `$CLAUDE_PROJECT_DIR/.claude/special-agents/state/session-<id>.json` with a 1-hour TTL; stale files are swept on each `ExitPlanMode`. Add to the consuming project's `.gitignore`:

```
.claude/special-agents/state/
.claude/plans/
```

## Layout

```
.claude-plugin/plugin.json
agents/
  junior-plan-implementer.agent.md
  plan-clarity-reviewer.agent.md
  plan-implementation-reviewer.agent.md
commands/
  implement.md
  review.md
hooks/
  hooks.json
  special-agents/
    _lib.py
    discard-state.py
    implementation-router.py
    inject-base-rules.py
    inject-rules-into-subagent.py
    plan-review-gate.py
```
