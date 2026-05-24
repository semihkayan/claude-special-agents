#!/usr/bin/env python3
import json
import sys

BASE_RULES = (
    "## Behavioral Rules\n"
    "1. Ultrathink — consider edge cases, trade-offs, and second-order effects.\n"
    "2. When coding, always seek maintainability, simplicity, minimal failure surface, idempotent & resume-safe steps and root-cause over workaround.\n"
    "3. Default no code comments — code should be self-explanatory.\n"
    "4. Be extremely concise.\n"
    "5. Don't assume — verify or ask.\n"
)


def main() -> int:
    sys.stdin.read()
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": BASE_RULES,
            }
        },
        sys.stdout,
        ensure_ascii=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
