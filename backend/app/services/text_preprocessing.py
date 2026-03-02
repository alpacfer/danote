from __future__ import annotations


def strip_inline_comments(text: str) -> str:
    """Remove inline comments beginning with '#' on each line."""
    if "#" not in text:
        return text

    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())
