#!/usr/bin/env python3
"""Fix Python 3.9 compatibility: datetime.UTC -> timezone.utc."""

import re
from pathlib import Path


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text

    # Case 1: from datetime import datetime, UTC
    text = re.sub(
        r"from datetime import\s+(.+?),\s*UTC",
        r"from datetime import \1, timezone",
        text,
    )

    # Case 2: from datetime import UTC (alone)
    text = re.sub(
        r"from datetime import\s+UTC\s*$",
        "from datetime import timezone",
        text,
        flags=re.MULTILINE,
    )

    # Case 3: standalone UTC usage -> timezone.utc
    # Avoid replacing substrings inside other words (e.g., "cutoff")
    text = re.sub(r"\bUTC\b", "timezone.utc", text)

    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"Fixed: {path}")
        return True
    return False


def main() -> None:
    fixed = 0
    for directory in ("chronopersona", "tests", "scripts"):
        root = Path(directory)
        if not root.exists():
            continue
        for pyfile in root.rglob("*.py"):
            if "__pycache__" in str(pyfile):
                continue
            if fix_file(pyfile):
                fixed += 1

    print(f"\nTotal files fixed: {fixed}")


if __name__ == "__main__":
    main()
