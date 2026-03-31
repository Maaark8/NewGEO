from __future__ import annotations

from difflib import unified_diff


def markdown_diff(original: str, rewritten: str) -> str:
    diff_lines = list(
        unified_diff(
            original.splitlines(),
            rewritten.splitlines(),
            fromfile="before.md",
            tofile="after.md",
            lineterm="",
        )
    )
    if not diff_lines:
        return "```diff\n# no changes\n```"
    return "```diff\n" + "\n".join(diff_lines) + "\n```"

