#!/usr/bin/env python3
import json
import sys

PLAN_RULES = (
    "## Rules\n"
    "- Don't assume — verify or ask\n"
    "- The plan file must be English\n"
    "- Shared library — for context-free code another caller could plausibly need:\n"
    "  1. Exists and fits → use it\n"
    "  2. Same responsibility, missing case → extend (keep backward compatibility if clean; otherwise migrate callers)\n"
    "  3. Nothing fits → add it minimally, following project conventions for placement\n"
    "\n"
    "  One caller justifies placement; abstraction requires two.\n"
)


def main() -> int:
    sys.stdin.read()
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": PLAN_RULES,
            }
        },
        sys.stdout,
        ensure_ascii=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
