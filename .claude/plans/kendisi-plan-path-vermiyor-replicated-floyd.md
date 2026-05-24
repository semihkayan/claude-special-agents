# Remove `plansDirectory` dependency: read plan from `ExitPlanMode` tool_input

## Context

The plugin's hook chain resolves the active plan by grepping the session transcript for a path matching `/\.claude/plans/[\w.-]+\.md`. This works only when the consuming project sets `plansDirectory: ".claude/plans"` in its `.claude/settings.json` — otherwise Claude never writes a plan file there, the regex finds no match, and `ExitPlanMode` is denied with `plan_path_not_in_transcript`.

Transcript inspection (real `~/.claude/projects/.../*.jsonl`) confirms `ExitPlanMode`'s `tool_input` already carries both:

- `plan` — full plan markdown as a string.
- `planFilePath` — absolute path Claude wrote the file to (when the harness gave Claude one).

So the regex/transcript dance is unnecessary. Switching to `tool_input` removes the `plansDirectory` requirement, drops transcript I/O, and gives an exact path instead of a regex inference.

## Approach

Single source of truth for the plan: `tool_input` on both `PreToolUse` and `PostToolUse` for `ExitPlanMode`. Path resolution is **pure** (no I/O writes); file materialization is the gate's job only — the router only reads.

- **Primary path source:** `tool_input.planFilePath`, populated when the harness emitted a "Plan File Info" system-reminder and Claude wrote the plan to that path before calling `ExitPlanMode`.
- **Fallback (defensive):** if `planFilePath` is absent, fall back to `${CLAUDE_PROJECT_DIR}/.claude/special-agents/plans/session-<sid>.md`. Deterministic from `session_id`, so gate (Pre) and router (Post) compute identical paths without sharing on-disk state.
- **Roles split — critical to avoid double-writes:**
  - `_lib.resolve_plan(payload, sid)` is pure: returns `(plan_text, plan_path, err)` reading from `tool_input.plan` / `tool_input.planFilePath` / fallback path's contents, in that order. Never writes.
  - **Gate** ensures the resolved path exists by calling `write_plan_atomic(plan_path, plan_text)` once if `not os.path.isfile(plan_path)`. Then performs marker-stripping writes as today.
  - **Router** never writes. Calls `resolve_plan` and uses the returned text/path read-only. By the time PostToolUse fires, the gate has already run its final-stage cleanup write, so the file on disk is the cleaned version — exactly what sub-agents should see.
- **Markers travel inline via `tool_input.plan`** between successive `ExitPlanMode` calls — Claude regenerates the plan in its own context each turn and includes any newly-added marker in the next `plan` field. So `_review_is_clean` and `_check_ambiguity` operate on `plan_text` from `tool_input`, not on file contents — even when fallback is active. No prompt wording change required: `SELF_REVIEW_BODY` / `CLARITY_BODY` say "edit the plan / append to the plan file"; in the harness-path case Claude edits its own file, in the fallback case Claude edits the plan in its message context — either way the marker lands in `tool_input.plan` on the next call.
- **Directory creation:** add `os.makedirs(os.path.dirname(path), exist_ok=True)` to `write_plan_atomic` so the fallback `.claude/special-agents/plans/` dir is created on first use.

## Files

### `hooks/special-agents/_lib.py`

- Delete `PLAN_PATH_REGEX` (line 25).
- Add `FALLBACK_PLANS_DIR = os.path.join(PROJECT_DIR, ".claude/special-agents/plans")` and `fallback_plan_path(sid) -> str` helper.
- Add `os.makedirs(os.path.dirname(path), exist_ok=True)` to `write_plan_atomic` (line 99).
- Replace `read_plan_from_payload` with **pure** `resolve_plan(payload, sid) -> (text, path, err)`:
  - Read `tool_input.plan` and `tool_input.planFilePath`.
  - If `planFilePath` present: return `(plan_text, plan_path, None)` if `plan_text` is non-empty, else backfill from file at `plan_path`, else `"plan_unavailable"`.
  - Else: compute `fp = fallback_plan_path(sid)`. If `plan_text` non-empty → return `(plan_text, fp, None)` (caller materializes the file). Else if file at `fp` exists → backfill from disk. Else → `"plan_unavailable"`.
  - **Never writes.** Caller is responsible for materializing the file if needed.

### `hooks/special-agents/plan-review-gate.py`

- Rename import: `read_plan_from_payload` → `resolve_plan`. Drop `write_plan_atomic` import only if unused (still needed for marker strips and fallback materialization).
- After `sid = validate_session_id(...)`, call `plan_text, plan_path, err = resolve_plan(payload, sid)`.
- Immediately after a successful resolve, materialize fallback if needed:
  ```python
  if not os.path.isfile(plan_path):
      write_plan_atomic(plan_path, plan_text)
  ```
- Collapse `PLAN_ERR` to a single `plan_unavailable` entry; drop the three transcript-related keys.
- The existing marker-strip `write_plan_atomic` calls at lines 136 and 151 stay as-is (they write cleaned content to `plan_path`).

### `hooks/special-agents/implementation-router.py`

- Rename import: `read_plan_from_payload` → `resolve_plan`.
- Move the `sid = validate_session_id(...)` block above the plan read.
- Call `plan_text, abs_plan_path, err = resolve_plan(payload, sid)`. On `err`, log and exit 0 (no deny path on PostToolUse).
- **No write.** Router only consumes text and path. Gate is guaranteed to have run first and ensured the file exists; the router reads.

### `README.md`

- Replace "Required project settings" section (lines ~30–45) with an "Optional project settings" note: nothing is required; `plansDirectory` becomes a UX preference, not a dependency. Plugin's own state under `.claude/special-agents/`.
- Update the recommended-gitignore block to drop `.claude/plans/` (consumer's concern, not the plugin's) and keep `.claude/special-agents/`.

### Bump

- `.claude-plugin/plugin.json`: `version: 0.1.0` → `0.2.0` (behavior-affecting: drops `plansDirectory` requirement; adds fallback state location).

## Out of scope

- The repo's legacy `.claude/hooks/special-agents/` copies are stale duplicates of the plugin's pre-refactor state; not touched here. User can delete `.claude/` separately when ready.
- `SessionState` TypedDict unchanged; no on-disk schema migration needed. Sessions in flight at upgrade time continue without breakage.

## Verification

1. **Static checks** — after edits, run from repo root:

   ```bash
   python3 -m py_compile hooks/special-agents/_lib.py hooks/special-agents/plan-review-gate.py hooks/special-agents/implementation-router.py
   python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))"
   grep -rn 'PLAN_PATH_REGEX\|plan_path_not_in_transcript\|transcript_unavailable\|plan_file_missing' hooks/ && echo "STALE REFS FOUND" || echo "clean"
   ```

2. **Fixture trace** — feed synthetic payloads to `plan-review-gate.py` via stdin and confirm stdout:
   - A (harness path, round 1): `tool_input={plan:"# P\n", planFilePath:"/tmp/p.md"}`, no pre-existing session state → denies with `SELF_REVIEW_BODY`. If `/tmp/p.md` doesn't exist, gate materializes it once.
   - B (fallback path, round 2): `tool_input={plan:"# P\n<!-- review-clean -->\n"}` (no `planFilePath`), pre-existing state stage=`PLAN_REVIEW` → fallback file created at `.claude/special-agents/plans/session-<sid>.md` with `<!-- review-clean -->` stripped; transitions to `CLARITY_CHECK`; denies with `CLARITY_BODY` carrying fallback path.
   - C (no plan at all): `tool_input={}` → emits deny with `plan_unavailable`.
   - D (router after gate's final stage): `tool_input` same as the one that drove the gate to CLARITY_CHECK exit with ambiguity=4. Expect router to read the cleaned plan text from `plan_path`, NOT re-write the file, emit routing directive for band `1–6 → sonnet_subagent`. Diff the plan file before/after router fire — must be byte-identical.

3. **End-to-end smoke** — install plugin into a throwaway project without `plansDirectory` set, run `/implement test`, verify pipeline completes through plan-review → clarity check → routing without `plan_path_not_in_transcript` errors. State files appear under `.claude/special-agents/state/`, fallback plan under `.claude/special-agents/plans/`.

4. **Backward compat** — with `plansDirectory: ".claude/plans"` set, repeat smoke test; verify the gate uses the consumer's path (via `tool_input.planFilePath`), not the fallback. No regression vs. current behavior.
