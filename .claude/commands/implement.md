---
description: Implement the given task
---

You are the lead for the given task.

## Start
Do not do anything before calling these tools.
1. Call EnterWorktree (skip if not a git repo)
2. Call EnterPlanMode

## Rules
- Don't assume — verify or ask
- The plan file must be English
- Shared library — for context-free code another caller could plausibly need:
  1. Exists and fits → use it
  2. Same responsibility, missing case → extend (keep backward compatibility if clean; otherwise migrate callers)
  3. Nothing fits → add it minimally, following project conventions for placement
  
  One caller justifies placement; abstraction requires two.
